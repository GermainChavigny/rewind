"""Updates from GitHub Releases.

The admin shows the installed version and the latest release; "Update" starts
`<install dir>/install.sh update` as a transient systemd user unit, so the
update survives the backend restart it ends with. install.sh reports its
progress in `<install dir>/update.json`, read back here.

Only an installed REWIND (install.sh writes REWIND_INSTALL_DIR in rewind.env)
can update itself; a development checkout only shows its version.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

DEFAULT_REPO = "GermainChavigny/rewind"
CHECK_TTL_S = 3600
# install.sh died without writing "done"/"failed" (power cut…): stop showing "running".
STALE_S = 30 * 60

Spawner = Callable[[list[str]], None]


def _spawn(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True, timeout=15)


def parse_version(text: str) -> tuple[int, ...]:
    """ "v0.5.10" → (0, 5, 10); anything unparsable sorts first."""
    parts = re.findall(r"\d+", text.split("-")[0].split("+")[0])
    return tuple(int(p) for p in parts[:3]) or (0,)


class Updater:
    def __init__(
        self,
        http: httpx.Client,
        version: str,
        install_dir: Path | None = None,
        repo: str = DEFAULT_REPO,
        spawn: Spawner = _spawn,
        clock: Callable[[], float] = time.time,
    ):
        self.http = http
        self.version = version
        self.install_dir = install_dir
        self.repo = repo
        self.spawn = spawn
        self.clock = clock
        self._latest: dict | None = None
        self._checked_at: float | None = None
        self._error: str | None = None

    @classmethod
    def from_env(cls, http: httpx.Client, version: str) -> Updater:
        install_dir = os.environ.get("REWIND_INSTALL_DIR")
        return cls(
            http,
            version,
            Path(install_dir) if install_dir else None,
            os.environ.get("REWIND_REPO") or DEFAULT_REPO,
        )

    @property
    def installed(self) -> bool:
        return bool(self.install_dir and (self.install_dir / "install.sh").is_file())

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        token_file = self.install_dir / "github-token" if self.install_dir else None
        if token_file and token_file.is_file():
            # Only while the repository is private (see install.sh).
            headers["Authorization"] = f"Bearer {token_file.read_text().strip()}"
        return headers

    def latest(self, force: bool = False) -> dict | None:
        """The latest release as {version, notes, url}, cached for an hour."""
        if (
            not force
            and self._checked_at is not None
            and self.clock() - self._checked_at < CHECK_TTL_S
        ):
            return self._latest
        self._checked_at = self.clock()
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        try:
            res = self.http.get(url, headers=self._headers(), timeout=10)
            if res.status_code == 404:
                self._error = "no_release"
                self._latest = None
                return None
            res.raise_for_status()
            data = res.json()
            self._latest = {
                "version": str(data["tag_name"]).lstrip("v"),
                "notes": (data.get("body") or "").strip(),
                "url": data.get("html_url"),
            }
            self._error = None
        except (httpx.HTTPError, ValueError, KeyError) as err:
            log.info("update check failed: %s", err)
            self._error = "unreachable"
        return self._latest

    def progress(self) -> dict | None:
        """What install.sh last wrote in update.json (None: no update run yet)."""
        if not self.install_dir:
            return None
        try:
            data = json.loads((self.install_dir / "update.json").read_text())
        except (OSError, ValueError):
            return None
        if data.get("state") == "running" and self.clock() - float(data.get("time", 0)) > STALE_S:
            data = {**data, "state": "failed", "message": "interrupted"}
        return data

    def running(self) -> bool:
        p = self.progress()
        return bool(p and p.get("state") == "running")

    def status(self, check: bool = False) -> dict:
        latest = self.latest(force=check)
        available = bool(latest and parse_version(latest["version"]) > parse_version(self.version))
        return {
            "current": self.version,
            "latest": latest["version"] if latest else None,
            "notes": latest["notes"] if latest else "",
            "url": latest["url"] if latest else None,
            "available": available,
            "can_update": self.installed,
            "progress": self.progress(),
            "error": self._error,
        }

    def start(self) -> str | None:
        """Starts install.sh update in the background. None = started, else why not:
        "not_installed" (a git checkout), "running" or "spawn_failed"."""
        if not self.installed or not self.install_dir:
            return "not_installed"
        if self.running():
            return "running"
        # Seen by the admin at once, before install.sh writes its own progress.
        state = self.install_dir / "update.json"
        state.write_text(
            json.dumps({"state": "running", "message": "starting", "time": self.clock()})
        )
        try:
            self.spawn(
                [
                    "systemd-run",
                    "--user",
                    "--unit=rewind-update",
                    "--collect",
                    "--quiet",
                    str(self.install_dir / "install.sh"),
                    "update",
                ]
            )
        except (OSError, subprocess.SubprocessError) as err:
            log.warning("cannot start the update: %s", err)
            state.write_text(
                json.dumps({"state": "failed", "message": str(err), "time": self.clock()})
            )
            return "spawn_failed"
        log.info("update started (%s → latest)", self.version)
        return None
