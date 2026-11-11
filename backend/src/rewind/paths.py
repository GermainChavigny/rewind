"""
Where REWIND keeps its files.

Everything can be overridden by environment variable; otherwise XDG
conventions are used (Linux and macOS alike):

    REWIND_DATA_DIR    ~/.local/share/rewind   SQLite database, posters, imports…
    REWIND_CONFIG_DIR  ~/.config/rewind        config.toml
    REWIND_MEDIA_DIR   <data>/media            movies and series
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _xdg(var: str, fallback: str) -> Path:
    value = os.environ.get(var)
    return Path(value) if value else Path.home() / fallback


@dataclass(frozen=True)
class Paths:
    data: Path
    config: Path
    media: Path

    @property
    def import_v1(self) -> Path:
        """Latest snapshot imported from v1 (see tools/import_v1.py)."""
        return self.data / "import" / "v1"

    @classmethod
    def from_env(cls) -> Paths:
        data = Path(
            os.environ.get("REWIND_DATA_DIR") or _xdg("XDG_DATA_HOME", ".local/share") / "rewind"
        )
        config = Path(
            os.environ.get("REWIND_CONFIG_DIR") or _xdg("XDG_CONFIG_HOME", ".config") / "rewind"
        )
        media = Path(os.environ.get("REWIND_MEDIA_DIR") or data / "media")
        return cls(data=data.expanduser(), config=config.expanduser(), media=media.expanduser())

    def ensure(self) -> Paths:
        for path in (self.data, self.config, self.media):
            path.mkdir(parents=True, exist_ok=True)
        return self
