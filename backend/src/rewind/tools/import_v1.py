"""
Import des données de la v1 — en LECTURE SEULE côté v1.

La v1 reste utilisée au quotidien pendant le développement de la v2. Cet outil
n'écrit donc JAMAIS dans ses dossiers ; il fabrique, côté v2 :

  <data>/import/v1/   copie instantanée de tv_data (JSON, secrets, affiches).
                      Remplacée en bloc à chaque import (rename atomique).
  <media>/            liens physiques (hardlinks) vers les vidéos et sous-titres
                      de ~/movies : zéro espace disque en plus, et supprimer un
                      fichier côté v2 ne retire que le lien — la v1 garde le sien.

Relançable à volonté : la base SQLite de la v2 est (re)construite à partir de
l'instantané (voir le module de migration, phase 1).
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from rewind.paths import Paths

# Fichiers de la v1 utiles à la migration (le reste est ignoré).
V1_JSON = (
    "library.json",
    "progression.json",
    "alarm.json",
    "secrets.json",
    "advisor_blacklist.json",
    "movies_progress.json",
)
V1_DIRS = ("posters",)

# Seuls les médias sont liés (pas les .exe/.bat/scripts qui traînent dans ~/movies).
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
            f"Instantané : {self.snapshot}",
            f"Fichiers de données copiés : {', '.join(self.copied) or 'aucun'}",
            f"Médias liés : {self.linked} nouveaux, {self.already_linked} déjà présents",
        ]
        if self.skipped:
            lines.append(f"Ignorés ({len(self.skipped)}) : " + ", ".join(self.skipped[:10]))
        if self.errors:
            lines.append("ERREURS :")
            lines += [f"  - {e}" for e in self.errors]
        return "\n".join(lines)


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _check_no_overlap(sources: list[Path], paths: Paths) -> None:
    """Refuse toute configuration où la v2 écrirait dans un dossier de la v1."""
    for src in sources:
        for dst in (paths.data, paths.media):
            if _is_inside(dst, src) or _is_inside(src, dst):
                raise ValueError(f"{dst} et {src} se chevauchent : import refusé (protection v1)")


def snapshot_data(tv_data: Path, paths: Paths, report: ImportReport) -> None:
    """Copie tv_data vers <data>/import/v1 via un dossier temporaire + rename."""
    target = paths.import_v1
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".v1-{int(time.time())}-{os.getpid()}"
    tmp.mkdir()
    try:
        for name in V1_JSON:
            src = tv_data / name
            if src.is_file():
                shutil.copy2(src, tmp / name)  # copy2 conserve le mode (secrets en 600)
                report.copied.append(name)
        for name in V1_DIRS:
            src = tv_data / name
            if src.is_dir():
                shutil.copytree(src, tmp / name)
                report.copied.append(f"{name}/")
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
    """Crée dans <media> un hardlink par vidéo/sous-titre de la v1."""
    if not movies.is_dir():
        report.errors.append(f"Dossier vidéos introuvable : {movies}")
        return
    if os.stat(movies).st_dev != os.stat(paths.media).st_dev:
        report.errors.append(
            f"{movies} et {paths.media} ne sont pas sur le même disque : liens physiques "
            "impossibles (et une copie doublerait l'espace utilisé)."
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
                # Fichier homonyme créé par la v2 : on n'y touche pas.
                report.skipped.append(f"{src.name} (existe déjà côté v2)")
            continue
        try:
            os.link(src, dst)
            report.linked += 1
        except OSError as err:
            report.errors.append(f"{src.name} : {err}")


def import_v1(tv_data: Path, movies: Path, paths: Paths) -> ImportReport:
    report = ImportReport()
    tv_data, movies = tv_data.expanduser(), movies.expanduser()
    if not tv_data.is_dir():
        report.errors.append(f"Dossier de données v1 introuvable : {tv_data}")
        return report
    _check_no_overlap([tv_data, movies], paths)
    snapshot_data(tv_data, paths, report)
    link_media(movies, paths, report)
    return report
