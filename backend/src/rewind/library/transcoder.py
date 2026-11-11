"""
ffmpeg preparation of a video for the kiosk's <video> element.

The plan goes from cheapest to most expensive (the mini PC CPU is weak):
  remux — H.264 + AAC/MP3: copy the streams into an MP4 (instant).
  audio — H.264 video but AC3/DTS… audio: copy the video, re-encode the audio.
  full  — anything else (HEVC, MPEG-2, AVI…): H.264 baseline 3.0, 720 wide, AAC.
Resolution is never a criterion: the browser scales on display.

Every audio track is kept (language switching), subtitles are extracted to
WebVTT on the side, `+faststart` lets playback start before the end of the
file, and the output is written to a temp file renamed at the end.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

ProgressCb = Callable[[float], None]

FULL = ["-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0", "-preset", "fast",
        "-vf", "scale=720:-2", "-c:a", "aac", "-b:a", "128k"]  # fmt: skip
AUDIO_ONLY = ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
REMUX = ["-c", "copy"]

WEB_VIDEO = {"h264"}
WEB_AUDIO = {"aac", "mp3"}
TEXT_SUBS = {"subrip", "srt", "ass", "ssa", "mov_text", "webvtt"}  # bitmap subs can't be VTT
SUB_LANGS = {"fre": "fr", "fra": "fr", "fr": "fr", "eng": "en", "en": "en"}


class Transcoder:
    def __init__(self, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self._process: subprocess.Popen | None = None

    def available(self) -> bool:
        return bool(shutil.which(self.ffmpeg) and shutil.which(self.ffprobe))

    # --- probing ----------------------------------------------------------------------

    def _probe(self, src: Path, *args: str) -> dict:
        try:
            out = subprocess.run(
                [self.ffprobe, "-v", "error", *args, "-of", "json", str(src)],
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            return json.loads(out or "{}")
        except (ValueError, subprocess.SubprocessError, OSError):
            return {}

    def duration(self, src: Path) -> float:
        try:
            return float(self._probe(src, "-show_entries", "format=duration")["format"]["duration"])
        except (KeyError, TypeError, ValueError):
            return 0.0

    def streams(self, src: Path) -> dict:
        """{vcodec, acodec} of the first video and audio streams."""
        info: dict = {}
        data = self._probe(src, "-show_entries", "stream=codec_type,codec_name")
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                info.setdefault("vcodec", s.get("codec_name"))
            elif s.get("codec_type") == "audio":
                info.setdefault("acodec", s.get("codec_name"))
        return info

    def plan(self, src: Path) -> str:
        info = self.streams(src)
        if info.get("vcodec") in WEB_VIDEO:
            return "remux" if info.get("acodec") in WEB_AUDIO else "audio"
        return "full"

    def audio_tracks(self, src: Path) -> list[dict]:
        """Audio tracks in mux order; `index` matches the browser's `audioTracks`."""
        data = self._probe(
            src, "-select_streams", "a", "-show_entries", "stream_tags=language,title"
        )
        return [
            {
                "index": i,
                "lang": ((s.get("tags") or {}).get("language") or "").lower(),
                "title": (s.get("tags") or {}).get("title") or "",
            }
            for i, s in enumerate(data.get("streams", []))
        ]

    def subtitle_streams(self, src: Path) -> list[tuple[int, str]]:
        data = self._probe(
            src,
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_name:stream_tags=language",
        )
        found = []
        for s in data.get("streams", []):
            lang = SUB_LANGS.get(((s.get("tags") or {}).get("language") or "").lower())
            if s.get("codec_name") in TEXT_SUBS and lang:
                found.append((s["index"], lang))
        return found

    # --- work ----------------------------------------------------------------------

    def extract_subtitles(self, src: Path, out_dir: Path, base: str) -> dict[str, str]:
        """Embedded fr/en text subtitles → WebVTT (first track per language)."""
        subs: dict[str, str] = {}
        for index, lang in self.subtitle_streams(src):
            if lang in subs:
                continue
            name = f"{base}.{lang}.vtt"
            out = out_dir / name
            result = subprocess.run(
                [self.ffmpeg, "-y", "-i", str(src), "-map", f"0:{index}", str(out)],
                capture_output=True,
                timeout=300,
            )
            if result.returncode == 0 and out.exists():
                subs[lang] = name
            else:
                out.unlink(missing_ok=True)
        return subs

    def prepare(self, src: Path, dst: Path, progress: ProgressCb | None = None) -> str:
        """Run the cheapest plan that makes `src` playable; returns the plan used."""
        plan = self.plan(src)
        recipe = {"remux": REMUX, "audio": AUDIO_ONLY, "full": FULL}[plan]
        log.info("%s: %s", src.name, plan)
        self._run(src, dst, recipe, progress)
        return plan

    def _run(self, src: Path, dst: Path, recipe: list[str], progress: ProgressCb | None) -> None:
        duration = self.duration(src)
        tmp = dst.with_suffix(".tmp.mp4")
        cmd = [
            self.ffmpeg, "-y", "-i", str(src),
            # First real video (V = not a cover picture), ALL audio tracks, no
            # muxed subtitles (extracted separately).
            "-map", "0:V:0", "-map", "0:a?", "-sn",
            *recipe, "-movflags", "+faststart",
            "-progress", "pipe:1", "-nostats", "-loglevel", "error", str(tmp),
        ]  # fmt: skip
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            assert self._process.stdout is not None
            for line in self._process.stdout:
                # out_time_ms is in microseconds, despite its name.
                m = re.match(r"out_time_ms=(\d+)", line.strip())
                if m and duration > 0 and progress:
                    progress(min(1.0, int(m.group(1)) / 1_000_000 / duration))
            self._process.wait()
            if self._process.returncode != 0:
                err = (self._process.stderr.read() if self._process.stderr else "")[-500:]
                raise RuntimeError(f"ffmpeg failed ({self._process.returncode}): {err}")
            os.replace(tmp, dst)
            if progress:
                progress(1.0)
        finally:
            tmp.unlink(missing_ok=True)
            self._process = None

    def cancel(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.kill()
