"""The TV computer itself: turning it off, and its address on the local network."""

from __future__ import annotations

import logging
import socket
import subprocess
from collections.abc import Callable

log = logging.getLogger(__name__)

Runner = Callable[[list[str]], None]


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True, timeout=15)


def poweroff(mode: str, run: Runner = _run) -> bool:
    """Turns the computer off ("poweroff") or only logs it ("fake").

    `systemctl poweroff` needs no password for the user of the active local
    session (polkit), which is the kiosk's user. True = the shutdown started.
    """
    if mode == "fake":
        log.info("fake shutdown: the computer would turn off now")
        return True
    if mode != "poweroff":
        return False
    try:
        run(["systemctl", "poweroff", "--no-ask-password"])
        return True
    except (OSError, subprocess.SubprocessError) as err:
        log.warning("cannot turn the computer off: %s", err)
        return False


def lan_address() -> str | None:
    """The computer's IP address on the local network (the default route's)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            # No packet is sent: connecting a UDP socket only picks the route.
            s.connect(("192.0.2.1", 9))
            ip = s.getsockname()[0]
        except OSError:
            return None
    return None if ip.startswith("127.") else ip
