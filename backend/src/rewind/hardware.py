"""What the TV computer offers, so the admin shows choices instead of asking for
names: video outputs and their modes (DRM sysfs, works without X) and audio
output ports (PulseAudio/PipeWire `pactl`). Also applies the A/V offset live."""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

DRM = Path("/sys/class/drm")
Runner = Callable[[list[str]], str]


def _run(args: list[str]) -> str:
    env = {"LC_ALL": "C", **_session_env()}
    return subprocess.run(
        args, capture_output=True, text=True, timeout=5, check=True, env=env
    ).stdout


def _session_env() -> dict[str, str]:
    # pactl needs the user's runtime dir (the service may not inherit it).
    keep = (
        "XDG_RUNTIME_DIR",
        "PULSE_SERVER",
        "HOME",
        "PATH",
        "DBUS_SESSION_BUS_ADDRESS",
        "DISPLAY",
        "XAUTHORITY",
    )
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return env


def displays(root: Path = DRM) -> list[dict]:
    """Connectors as {name: "HDMI-A-2", connected, modes: [...]} (preferred mode first)."""
    out = []
    for conn in sorted(root.glob("card*-*")):
        status = conn / "status"
        if not status.is_file():
            continue
        name = conn.name.split("-", 1)[1]  # card0-HDMI-A-2 → HDMI-A-2
        try:
            modes_text = (conn / "modes").read_text()
            connected = status.read_text().strip() == "connected"
        except OSError:
            continue
        modes: list[str] = []
        for line in modes_text.split():
            if line not in modes:
                modes.append(line)
        out.append({"name": name, "connected": connected, "modes": modes})
    out.sort(key=lambda d: not d["connected"])
    return out


_PORT = re.compile(
    r"^\t\t(?P<name>[\w.-]+): (?P<desc>.*) \(type: (?P<type>[^,]*),.*latency offset: "
    r"(?P<offset>-?\d+) usec, (?P<avail>[^)]*)\)$"
)


def audio_ports(run: Runner = _run) -> list[dict]:
    """Output ports as {card, name, description, available, offset_ms}."""
    try:
        text = run(["pactl", "list", "cards"])
    except (OSError, subprocess.SubprocessError) as err:
        log.info("pactl unavailable: %s", err)
        return []
    ports: list[dict] = []
    card = card_desc = None
    in_ports = False
    for line in text.splitlines():
        if line.startswith("Card #"):
            card = card_desc = None
            in_ports = False
        elif line.startswith("\tName: "):
            card = line.split(": ", 1)[1].strip()
        elif "device.description = " in line and card_desc is None:
            card_desc = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("\tPorts:"):
            in_ports = True
        elif in_ports and (m := _PORT.match(line)):
            if "output" not in m["name"]:
                continue
            ports.append(
                {
                    "card": card,
                    "card_description": card_desc or card,
                    "name": m["name"],
                    "description": m["desc"],
                    "available": m["avail"] != "not available",
                    "offset_ms": round(int(m["offset"]) / 1000),
                }
            )
        elif in_ports and line.startswith("\t") and not line.startswith("\t\t"):
            in_ports = False
    return ports


def apply_av_offset(port: str | None, offset_ms: int, run: Runner = _run) -> bool:
    """Sets the latency offset of `port` now (on the card that has it)."""
    if not port:
        return False
    for p in audio_ports(run):
        if p["name"] == port:
            try:
                run(["pactl", "set-port-latency-offset", p["card"], port, str(offset_ms * 1000)])
                return True
            except (OSError, subprocess.SubprocessError) as err:
                log.warning("cannot set the A/V offset: %s", err)
                return False
    return False


def wayland_sockets() -> list[str]:
    """Wayland displays of the user (cage's), e.g. ["wayland-0"]."""
    runtime = Path(_session_env()["XDG_RUNTIME_DIR"])
    try:
        return sorted(p.name for p in runtime.glob("wayland-*") if not p.name.endswith(".lock"))
    except OSError:
        return []


def apply_display(
    output: str | None,
    mode: str | None,
    run: Runner = _run,
    wayland: list[str] | None = None,
) -> bool:
    """Switches the video output/mode now: cage (`wlr-randr`) or X11 (`xrandr`).
    False = only at the next start."""
    if not output:
        return False
    for socket in wayland_sockets() if wayland is None else wayland:
        try:
            # Same DRM names (HDMI-A-2) as the config.
            args = ["--mode", mode] if mode else ["--preferred"]
            run(["env", f"WAYLAND_DISPLAY={socket}", "wlr-randr", "--output", output, *args])
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    # Config uses DRM names (HDMI-A-2); X11 calls it HDMI-2.
    names = [output.replace("HDMI-A-", "HDMI-"), output]
    args = ["--mode", mode] if mode else ["--auto"]
    for name in dict.fromkeys(names):
        try:
            run(["xrandr", "--output", name, *args])
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    log.info("cannot switch the display to %s %s now", output, mode or "auto")
    return False
