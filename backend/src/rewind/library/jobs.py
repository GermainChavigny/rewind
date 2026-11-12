"""
Download / transcode jobs.

Two stages: several DOWNLOADS in parallel (network bound) but ONE TRANSCODE at
a time (the mini PC can't run two heavy ffmpeg). Downloads are prioritized by
(season, episode) so the lowest episodes start first. All job state lives in
the database (status, progress, error), so jobs resume after a reboot.

A job is a media row:
  movie   — magnet (or local file) → subtitles → transcode → ready
  pack    — a series torrent (one episode, a season or the whole show): its
            video files are mapped to target episodes (SxxEyy), each becomes an
            `episode` row sent to the transcode stage; targets missing from the
            pack are handed back to the series manager (single-episode fallback).
"""

from __future__ import annotations

import logging
import queue
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path

from rewind.db import Database, now
from rewind.library.sources import parse_episode
from rewind.library.subtitles import OpenSubtitles
from rewind.library.torrent import Cancelled, TorrentClient
from rewind.library.transcoder import Transcoder

log = logging.getLogger(__name__)

ACTIVE = ("queued", "downloading", "fetching-subs", "transcoding")


def episode_id(show_id: str, season: int, episode: int) -> str:
    return f"{show_id}-s{int(season):02d}e{int(episode):02d}"


def priority(item: dict) -> int:
    """Movies first (explicit requests), then the lowest season/episode."""
    if item["kind"] == "episode":
        return (item.get("season") or 0) * 1000 + (item.get("episode") or 0)
    if item["kind"] == "pack":
        targets = item.get("targets") or []
        if targets:
            return min(t["season"] * 1000 + t["episode"] for t in targets)
        return (item.get("season") or 0) * 1000
    return 0


class JobWorker:
    def __init__(
        self,
        db: Database,
        media_dir: Path,
        downloads_dir: Path,
        torrent: TorrentClient,
        transcoder: Transcoder,
        subtitles: Callable[[], OpenSubtitles | None],
        languages: Callable[[], list[str]],
        slots: int = 3,
    ):
        self.db = db
        self.media_dir = media_dir
        self.downloads_dir = downloads_dir
        self.torrent = torrent
        self.transcoder = transcoder
        self.subtitles = subtitles
        self.languages = languages
        self.slots = slots
        # Called with (pack, missing_targets) when a pack lacks some episodes.
        self.on_pack_missing: Callable[[dict, list[dict]], None] | None = None
        self._dl: queue.PriorityQueue = queue.PriorityQueue()
        self._tc: queue.Queue = queue.Queue()
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._cancelled: set[str] = set()
        self._transcoding: str | None = None
        self._started = False
        self._threads = 0
        self._slots_changed = threading.Condition()

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.set_slots(self.slots)
        threading.Thread(target=self._transcode_loop, daemon=True, name="transcode").start()
        self.resume_pending()

    def set_slots(self, slots: int) -> None:
        """Changes the number of parallel downloads at once (no restart).

        Threads are only ever added: a thread whose index is above the new
        count finishes its current job, then waits until slots go up again.
        """
        with self._slots_changed:
            self.slots = max(1, slots)
            if self._started:
                while self._threads < self.slots:
                    i = self._threads
                    self._threads += 1
                    threading.Thread(
                        target=self._download_loop, args=(i,), daemon=True, name=f"dl-{i}"
                    ).start()
            self._slots_changed.notify_all()

    # --- API --------------------------------------------------------------------------

    def enqueue(self, item_id: str) -> None:
        self._cancelled.discard(item_id)
        item = self.db.get_media(item_id) or {"kind": "movie"}
        with self._seq_lock:
            self._seq += 1
            self._dl.put((priority(item), self._seq, item_id))

    def cancel(self, item_id: str) -> None:
        self._cancelled.add(item_id)
        if item_id == self._transcoding:
            self.transcoder.cancel()
        self.db.patch_media(item_id, {"status": "error", "error": "cancelled"})

    def resume_pending(self) -> None:
        """Re-queue movies and packs interrupted by a reboot (episodes resume via their pack)."""
        for item in self.db.list_media():
            if item["status"] in ACTIVE and item["kind"] in ("movie", "pack"):
                log.info("resuming job %s", item["id"])
                self.db.patch_media(item["id"], {"status": "queued"})
                self.enqueue(item["id"])

    def active_jobs(self) -> dict[str, dict]:
        return {
            item["id"]: {
                "title": item["title"],
                "status": item["status"],
                "progress": item.get("progress") or {},
                "error": item.get("error"),
                "kind": item["kind"],
                "parent_id": item.get("parent_id"),
                "season": item.get("season"),
                "episode": item.get("episode"),
            }
            for item in self.db.list_media()
            if item["status"] != "ready" and item["kind"] != "series"
        }

    # --- loops ------------------------------------------------------------------------

    def _download_loop(self, index: int = 0) -> None:
        while True:
            with self._slots_changed:
                self._slots_changed.wait_for(lambda: index < self.slots)
            _, _, item_id = self._dl.get()
            item = self.db.get_media(item_id)
            if item_id in self._cancelled or not item:
                continue
            try:
                if item["kind"] == "pack":
                    self._download_pack(item)
                else:
                    self._download_movie(item)
            except Cancelled:
                pass
            except Exception as err:  # noqa: BLE001 - worker threads never die
                log.warning("download %s failed: %s", item_id, err)
                self.db.patch_media(item_id, {"status": "error", "error": str(err)})

    def _transcode_loop(self) -> None:
        while True:
            item_id = self._tc.get()
            item = self.db.get_media(item_id)
            if not item:
                continue
            try:
                if item_id not in self._cancelled:
                    self._transcoding = item_id
                    self._finalize(item)
            except Exception as err:  # noqa: BLE001
                log.warning("transcode %s failed: %s", item_id, err)
                if item_id not in self._cancelled:
                    self.db.patch_media(item_id, {"status": "error", "error": str(err)})
            finally:
                self._transcoding = None
                self._after_transcode(self.db.get_media(item_id) or item)

    # --- stages -----------------------------------------------------------------------

    def _progress(self, item_id: str, key: str) -> Callable[[float], None]:
        """Progress callback writing to the database at most every 2 s."""
        last = [0.0]

        def cb(ratio: float) -> None:
            t = time.monotonic()
            if t - last[0] >= 2 or ratio >= 1:
                last[0] = t
                current = self.db.get_media(item_id)
                if current:
                    progress = {**(current.get("progress") or {}), key: round(ratio, 3)}
                    self.db.patch_media(item_id, {"progress": progress})

        return cb

    def _source(self, item: dict) -> Path | None:
        if (staged := item.get("staging_file")) and Path(staged).exists():
            return Path(staged)
        if local := item.get("local_source"):
            path = Path(local)
            return path if path.is_absolute() else self.media_dir / path
        return None

    def _download_movie(self, item: dict) -> None:
        item_id = item["id"]
        src = self._source(item)
        if src is None and item.get("magnet"):
            self.db.patch_media(item_id, {"status": "downloading", "error": None})
            files = self.torrent.download(
                item["magnet"],
                progress=self._progress(item_id, "download"),
                cancelled=lambda: item_id in self._cancelled,
            )
            src = max(files, key=lambda p: p.stat().st_size)
            self.db.patch_media(item_id, {"staging_file": str(src)})
        if src is None or not src.exists():
            raise RuntimeError(f"source file not found: {src}")
        self.db.patch_media(
            item_id,
            {"status": "transcoding", "progress": {**(item.get("progress") or {}), "transcode": 0}},
        )
        self._tc.put(item_id)

    def _download_pack(self, pack: dict) -> None:
        pack_id = pack["id"]
        self.db.patch_media(pack_id, {"status": "downloading", "error": None})
        # Try each candidate (most seeded first): many come from private trackers
        # whose peers are unreachable without a passkey.
        candidates = pack.get("candidates") or []
        videos, last_err = None, None
        for i, magnet in enumerate(candidates):
            if pack_id in self._cancelled:
                return
            try:
                videos = self.torrent.download(
                    magnet,
                    progress=self._progress(pack_id, "download"),
                    cancelled=lambda: pack_id in self._cancelled,
                    meta_timeout=45,
                )
                break
            except Cancelled:
                return
            except RuntimeError as err:
                last_err = err
                log.info(
                    "pack %s: candidate %d/%d failed (%s)", pack_id, i + 1, len(candidates), err
                )
                self.db.patch_media(pack_id, {"progress": {"download": 0}})
        if not videos:
            raise RuntimeError(str(last_err or "no usable source"))

        by_key: dict[tuple[int, int], Path] = {}
        for path in videos:
            parsed = parse_episode(path.name)
            if parsed and parsed[1] is not None:
                by_key.setdefault((parsed[0], parsed[1]), path)

        matched, missing = [], []
        for target in pack.get("targets") or []:
            existing = self.db.get_media(target["episode_id"])
            if existing and existing["status"] == "ready":
                continue
            src = by_key.get((target["season"], target["episode"]))
            if src:
                matched.append((target, src))
            else:
                missing.append(target)
        log.info(
            "pack %s: %d files, %d episodes recognized, %d matched, %d missing",
            pack_id, len(videos), len(by_key), len(matched), len(missing),
        )  # fmt: skip

        if not matched:
            self._cleanup(videos)
            self.db.delete_media(pack_id)
        else:
            # The counter is set BEFORE queuing: the transcoder must not finish an
            # episode before it exists.
            self.db.patch_media(
                pack_id,
                {
                    "status": "transcoding",
                    "pending_episodes": len(matched),
                    "staging_files": [str(p) for p in videos],
                },
            )
            for target, src in matched:
                self.db.upsert_media(self._episode(pack, target, src))
                self._tc.put(target["episode_id"])
        if missing and pack.get("fallback") and self.on_pack_missing:
            self.on_pack_missing(pack, missing)

    def _episode(self, pack: dict, target: dict, src: Path) -> dict:
        s, e = target["season"], target["episode"]
        return {
            "id": target["episode_id"],
            "kind": "episode",
            "parent_id": pack["parent_id"],
            "title": f"{pack.get('show_title') or ''} S{s:02d}E{e:02d}".strip(),
            "year": pack.get("year"),
            "season": s,
            "episode": e,
            "status": "transcoding",
            "file": f"{target['episode_id']}.mp4",
            "added_at": now(),
            "tmdb_id": pack.get("tmdb_id"),
            "episode_title": target.get("title"),
            "subtitles": {},
            "subtitle_offsets": {},
            "progress": {"transcode": 0},
            "staging_file": str(src),
            "pack_id": pack["id"],
            "error": None,
        }

    def _finalize(self, item: dict) -> None:
        """Subtitles + transcode + metadata of ONE file."""
        item_id = item["id"]
        src = self._source(item)
        if src is None or not src.exists():
            raise RuntimeError(f"source file not found: {src}")

        # a) embedded subtitles: same cut as the video → perfect sync;
        # b) missing languages: OpenSubtitles, matched on the release.
        self.db.patch_media(item_id, {"status": "fetching-subs"})
        langs = self.languages()
        subs = self.transcoder.extract_subtitles(src, self.media_dir, item_id, langs)
        missing = [lang for lang in langs if lang not in subs]
        client = self.subtitles()
        if missing and client:
            try:
                subs.update(
                    client.fetch(
                        self.media_dir,
                        item_id,
                        missing,
                        video=src,
                        imdb_id=item.get("imdb_id"),
                        tmdb_id=item.get("tmdb_id"),
                        title=item.get("title"),
                        year=item.get("year"),
                        season=item.get("season"),
                        episode=item.get("episode"),
                    )
                )
            except Exception as err:  # noqa: BLE001 - subtitles never block a movie
                log.warning("subtitles unavailable for %s: %s", item_id, err)

        self.db.patch_media(item_id, {"status": "transcoding", "error": None})
        dst = self.media_dir / (item.get("file") or f"{item_id}.mp4")
        self.transcoder.prepare(src, dst, self._progress(item_id, "transcode"))
        if item_id in self._cancelled:
            dst.unlink(missing_ok=True)
            return
        current = self.db.get_media(item_id) or item
        self.db.patch_media(
            item_id,
            {
                "status": "ready",
                "file": dst.name,
                "subtitles": {**(current.get("subtitles") or {}), **subs},
                "duration": self.transcoder.duration(dst),
                "audio_tracks": self.transcoder.audio_tracks(dst),
                "error": None,
            },
        )
        log.info("%s ready (%s)", item_id, dst.name)

    def _after_transcode(self, item: dict) -> None:
        """Clean the staging files: a movie's own, or a pack's once its last episode is done."""
        if item["kind"] == "episode":
            pack = self.db.get_media(item.get("pack_id") or "")
            if not pack:
                return
            left = (pack.get("pending_episodes") or 1) - 1
            if left <= 0:
                self._cleanup([Path(p) for p in pack.get("staging_files") or []])
                self.db.delete_media(pack["id"])
            else:
                self.db.patch_media(pack["id"], {"pending_episodes": left})
            self.db.patch_media(item["id"], {"staging_file": None})
        elif (staged := item.get("staging_file")) and (
            # A failed transcode keeps the download, so a retry doesn't fetch it again.
            item["status"] == "ready" or item["id"] in self._cancelled
        ):
            self._cleanup([Path(staged)])
            self.db.patch_media(item["id"], {"staging_file": None})

    def _cleanup(self, files: list[Path]) -> None:
        """Remove downloaded files (the torrent's own folder when it made one)."""
        for path in files:
            try:
                parent = path.parent
                if parent != self.downloads_dir and parent.is_relative_to(self.downloads_dir):
                    shutil.rmtree(parent, ignore_errors=True)
                elif path.is_relative_to(self.downloads_dir):
                    path.unlink(missing_ok=True)
            except OSError as err:
                log.warning("cleanup of %s failed: %s", path, err)
