"""
External subtitles from OpenSubtitles (API key + free account), converted to
WebVTT. The release is matched by its `moviehash` first (subtitles timed for
THIS file), then by IMDb/TMDB id or title. Downloaded subtitles are re-timed
on the soundtrack with ffsubsync when it is installed.
"""

from __future__ import annotations

import logging
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


def moviehash(path: Path) -> str | None:
    """OpenSubtitles hash: file size + 64-bit sums of the first and last 64 KiB."""
    chunk = 65536
    try:
        size = path.stat().st_size
        if size < chunk * 2:
            return None
        h = size
        with open(path, "rb") as f:
            for offset in (0, size - chunk):
                f.seek(offset)
                for (value,) in struct.iter_unpack("<q", f.read(chunk)):
                    h = (h + value) & 0xFFFFFFFFFFFFFFFF
        return f"{h:016x}"
    except (OSError, struct.error):
        return None


def _ffsubsync() -> str | None:
    found = shutil.which("ffsubsync")
    if found:
        return found
    venv = Path(sys.prefix) / "bin" / "ffsubsync"  # installed with REWIND, not on PATH
    return str(venv) if os.access(venv, os.X_OK) else None


class OpenSubtitles:
    BASE = "https://api.opensubtitles.com/api/v1"

    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        http: httpx.Client,
        ffmpeg: str = "ffmpeg",
    ):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.http = http
        self.ffmpeg = ffmpeg
        self._token: str | None = None
        self._token_at = 0.0

    def available(self) -> bool:
        return bool(self.api_key and self.username and self.password)

    def _headers(self, auth: bool = False) -> dict:
        h = {"Api-Key": self.api_key, "User-Agent": "rewind v0.1", "Accept": "application/json"}
        if auth and self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _login(self) -> None:
        if self._token and time.time() - self._token_at < 20 * 3600:
            return
        resp = self.http.post(
            f"{self.BASE}/login",
            json={"username": self.username, "password": self.password},
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json().get("token")
        self._token_at = time.time()

    def fetch(
        self,
        out_dir: Path,
        base: str,
        langs: list[str],
        video: Path | None = None,
        imdb_id: str | None = None,
        tmdb_id: int | None = None,
        title: str | None = None,
        year: int | None = None,
        season: int | None = None,
        episode: int | None = None,
    ) -> dict[str, str]:
        """Download the best subtitles per language; returns {lang: file.vtt}."""
        if not self.available() or not langs:
            return {}
        self._login()
        movie_hash = moviehash(video) if video else None
        out: dict[str, str] = {}
        for lang in langs:
            try:
                file_id = self._best(
                    lang, movie_hash, imdb_id, tmdb_id, title, year, season, episode
                )
                srt = self._download(file_id) if file_id else None
                name = self._to_vtt(srt, out_dir, base, lang) if srt else None
                if not name:
                    continue
                if video:
                    self.resync(out_dir / name, video)
                out[lang] = name
            except httpx.HTTPError as err:
                log.warning("OpenSubtitles %s: %s", lang, err)
        return out

    def _best(self, lang, movie_hash, imdb_id, tmdb_id, title, year, season, episode):
        # OpenSubtitles splits Portuguese and Chinese into regional variants.
        code = {"pt": "pt-pt,pt-br", "zh": "zh-cn,zh-tw"}.get(lang, lang)
        params: dict = {"languages": code, "order_by": "download_count"}
        if movie_hash:
            params["moviehash"] = movie_hash
        if season is not None:
            params["season_number"] = season
        if episode is not None:
            params["episode_number"] = episode
        if imdb_id:
            params["imdb_id"] = str(imdb_id).removeprefix("tt")
        elif tmdb_id:
            params["tmdb_id"] = tmdb_id
        elif title:
            params["query"] = title
            if year:
                params["year"] = year
        elif not movie_hash:
            return None
        resp = self.http.get(
            f"{self.BASE}/subtitles", params=params, headers=self._headers(), timeout=10
        )
        resp.raise_for_status()
        items = resp.json().get("data") or []
        # Exact-release matches first.
        items.sort(key=lambda it: not (it.get("attributes") or {}).get("moviehash_match"))
        for item in items:
            files = (item.get("attributes") or {}).get("files") or []
            if files:
                return files[0].get("file_id")
        return None

    def _download(self, file_id: int) -> bytes | None:
        resp = self.http.post(
            f"{self.BASE}/download",
            json={"file_id": file_id},
            headers=self._headers(auth=True),
            timeout=10,
        )
        resp.raise_for_status()
        link = resp.json().get("link")
        if not link:
            return None
        srt = self.http.get(link, timeout=20)
        srt.raise_for_status()
        return srt.content

    def _to_vtt(self, srt: bytes, out_dir: Path, base: str, lang: str) -> str | None:
        name = f"{base}.{lang}.vtt"
        out = out_dir / name
        proc = subprocess.run(
            [self.ffmpeg, "-y", "-f", "srt", "-i", "pipe:0", str(out)],
            input=srt,
            capture_output=True,
            timeout=60,
        )
        if proc.returncode == 0 and out.exists():
            return name
        out.unlink(missing_ok=True)
        return None

    @staticmethod
    def resync(vtt: Path, video: Path) -> bool:
        """Re-time a subtitle file on the soundtrack (best effort, in place)."""
        tool = _ffsubsync()
        if not tool:
            return False
        tmp = vtt.with_suffix(".synced.vtt")
        try:
            proc = subprocess.run(
                [tool, str(video), "-i", str(vtt), "-o", str(tmp)],
                capture_output=True,
                timeout=600,
            )
            if proc.returncode == 0 and tmp.exists():
                os.replace(tmp, vtt)
                return True
            log.warning("ffsubsync failed on %s (%s)", vtt.name, proc.returncode)
        except (OSError, subprocess.SubprocessError) as err:
            log.warning("ffsubsync unavailable: %s", err)
        finally:
            tmp.unlink(missing_ok=True)
        return False
