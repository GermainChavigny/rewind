"""
Import v1 data — strictly READ-ONLY on the v1 side.

v1 stays in daily use while v2 is being developed, so this tool NEVER writes
into its folders. On the v2 side it produces:

  <data>/import/v1/   snapshot copy of tv_data (JSON, secrets, posters).
                      Replaced as a whole on every import (atomic rename).
  <media>/            hardlinks to the videos and subtitles in ~/movies: no
                      extra disk space, and deleting a file on the v2 side only
                      removes the link — v1 keeps its own.

Safe to re-run: the v2 SQLite database is (re)built from the snapshot (see the
migration module, phase 1).
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from rewind.paths import Paths

# v1 files needed for the migration (everything else is ignored).
V1_JSON = (
    "library.json",
    "progression.json",
    "alarm.json",
    "secrets.json",
    "advisor_blacklist.json",
    "movies_progress.json",
)
V1_DIRS = ("posters",)

# v1 app files holding settings that were hardcoded there (channels, smart plug
# IP, weather location, logos), plus ~/.xinitrc (A/V offset, video output).
V1_APP_FILES = ("modules/StateManager.js", "api.py", "config.js")
V1_APP_DIRS: tuple[str, ...] = ()  # v1 logos are not used by v2

# Only media files are linked (not the stray .exe/.bat/scripts in ~/movies).
MEDIA_EXTS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".m4v",
    ".webm",
    ".ts",
    ".wmv",
    ".flv",
    ".vtt",
    ".srt",
}


@dataclass
class ImportReport:
    snapshot: Path | None = None
    copied: list[str] = field(default_factory=list)
    linked: int = 0
    already_linked: int = 0
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        lines = [
            f"Snapshot: {self.snapshot}",
            f"Data files copied: {', '.join(self.copied) or 'none'}",
            f"Media linked: {self.linked} new, {self.already_linked} already present",
        ]
        if self.skipped:
            lines.append(f"Skipped ({len(self.skipped)}): " + ", ".join(self.skipped[:10]))
        if self.errors:
            lines.append("ERRORS:")
            lines += [f"  - {e}" for e in self.errors]
        return "\n".join(lines)


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _check_no_overlap(sources: list[Path], paths: Paths) -> None:
    """Refuse any setup where v2 would write inside a v1 folder."""
    for src in sources:
        for dst in (paths.data, paths.media):
            if _is_inside(dst, src) or _is_inside(src, dst):
                raise ValueError(f"{dst} and {src} overlap: import refused (v1 protection)")


def snapshot_data(
    tv_data: Path,
    paths: Paths,
    report: ImportReport,
    app_dir: Path | None = None,
    xinitrc: Path | None = None,
) -> None:
    """Copy tv_data (+ v1 app settings files) to <data>/import/v1 via a temp dir + rename."""
    target = paths.import_v1
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".v1-{int(time.time())}-{os.getpid()}"
    tmp.mkdir()
    try:
        for name in V1_JSON:
            src = tv_data / name
            if src.is_file():
                shutil.copy2(src, tmp / name)  # copy2 keeps the mode (secrets stay 600)
                report.copied.append(name)
        for name in V1_DIRS:
            src = tv_data / name
            if src.is_dir():
                shutil.copytree(src, tmp / name)
                report.copied.append(f"{name}/")
        if app_dir and app_dir.is_dir():
            for rel in V1_APP_FILES:
                src = app_dir / rel
                if src.is_file():
                    (tmp / "app" / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, tmp / "app" / rel)
                    report.copied.append(f"app/{rel}")
            for rel in V1_APP_DIRS:
                if (app_dir / rel).is_dir():
                    shutil.copytree(app_dir / rel, tmp / "app" / rel)
                    report.copied.append(f"app/{rel}/")
        if xinitrc and xinitrc.is_file():
            shutil.copy2(xinitrc, tmp / "xinitrc")
            report.copied.append("xinitrc")
        (tmp / "IMPORTED_AT").write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z\n"))

        old = None
        if target.exists():
            old = target.parent / f".v1-old-{int(time.time())}-{os.getpid()}"
            target.rename(old)
        tmp.rename(target)
        if old:
            shutil.rmtree(old, ignore_errors=True)
        report.snapshot = target
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def link_media(movies: Path, paths: Paths, report: ImportReport) -> None:
    """Create one hardlink in <media> per v1 video/subtitle file."""
    if not movies.is_dir():
        report.errors.append(f"Videos folder not found: {movies}")
        return
    if os.stat(movies).st_dev != os.stat(paths.media).st_dev:
        report.errors.append(
            f"{movies} and {paths.media} are not on the same filesystem: hardlinks "
            "are impossible (and a copy would double the disk usage)."
        )
        return

    for src in sorted(movies.iterdir()):
        if not src.is_file() or src.is_symlink():
            continue
        if src.suffix.lower() not in MEDIA_EXTS:
            report.skipped.append(src.name)
            continue
        dst = paths.media / src.name
        if dst.exists():
            if os.path.samefile(src, dst):
                report.already_linked += 1
            else:
                # Same-name file created by v2: leave it alone.
                report.skipped.append(f"{src.name} (already exists on the v2 side)")
            continue
        try:
            os.link(src, dst)
            report.linked += 1
        except OSError as err:
            report.errors.append(f"{src.name}: {err}")


def import_v1(
    tv_data: Path,
    movies: Path,
    paths: Paths,
    app_dir: Path | None = None,
    xinitrc: Path | None = None,
) -> ImportReport:
    report = ImportReport()
    tv_data, movies = tv_data.expanduser(), movies.expanduser()
    if not tv_data.is_dir():
        report.errors.append(f"v1 data folder not found: {tv_data}")
        return report
    _check_no_overlap([p for p in (tv_data, movies, app_dir) if p], paths)
    snapshot_data(tv_data, paths, report, app_dir, xinitrc)
    link_media(movies, paths, report)
    return report
