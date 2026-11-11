"""
The library service: one object per app, used by the routes. External
clients (indexers, TMDB, OpenSubtitles, AI providers) are rebuilt from the
live config, so keys changed in the admin apply at once.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from rewind.config import Config
from rewind.context import AppContext
from rewind.db import now
from rewind.library import advisor as adv
from rewind.library.jobs import ACTIVE, JobWorker
from rewind.library.series import SeriesManager
from rewind.library.sources import Indexers, Tmdb, clean_title, slugify
from rewind.library.subtitles import OpenSubtitles
from rewind.library.torrent import Prober, TorrentClient
from rewind.library.transcoder import Transcoder

log = logging.getLogger(__name__)

RECHECK_EVERY_S = 12 * 3600


class LibraryError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class LibraryService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.db = ctx.db
        self.media_dir = ctx.paths.media
        self.posters_dir = ctx.paths.data / "posters"
        self.downloads_dir = ctx.paths.data / "downloads"
        for d in (self.posters_dir, self.downloads_dir):
            d.mkdir(parents=True, exist_ok=True)
        lib = self.config.library
        self.transcoder = Transcoder()
        self.torrent = TorrentClient(self.downloads_dir, lib.torrent_port)
        self.prober = Prober(self.downloads_dir / "_probe", lib.torrent_port + 8)
        self._subs: OpenSubtitles | None = None
        self.worker = JobWorker(
            self.db,
            self.media_dir,
            self.downloads_dir,
            self.torrent,
            self.transcoder,
            subtitles=self.subtitles,
            languages=lambda: self.config.opensubtitles.languages,
            slots=lib.download_slots,
        )
        self.series = SeriesManager(
            self.db, self.worker, self.posters_dir, tmdb=self.tmdb, indexers=self.indexers
        )

    @property
    def config(self) -> Config:
        return self.ctx.config

    def start(self) -> None:
        """Start the job threads (resuming interrupted jobs) and the background chores."""
        self.worker.start()
        threading.Thread(target=self._chores, daemon=True, name="library-chores").start()

    def _chores(self) -> None:
        self.backfill_overviews()
        while True:
            try:
                self.series.recheck_airing()
            except Exception as err:  # noqa: BLE001
                log.warning("series recheck failed: %s", err)
            time.sleep(RECHECK_EVERY_S)

    # --- clients ----------------------------------------------------------------------

    def tmdb(self) -> Tmdb:
        return Tmdb(self.config.tmdb.api_key, self.config.tmdb.language, self.ctx.http)

    def indexers(self) -> Indexers:
        return Indexers(self.config.indexers, self.ctx.http)

    def subtitles(self) -> OpenSubtitles | None:
        cfg = self.config.opensubtitles
        key = (cfg.api_key, cfg.username, cfg.password)
        if (
            self._subs is None
            or (self._subs.api_key, self._subs.username, self._subs.password) != key
        ):
            self._subs = OpenSubtitles(*key, http=self.ctx.http)
        return self._subs if self._subs.available() else None

    def features(self) -> dict[str, bool]:
        return {
            "search": bool(self.config.indexers) and TorrentClient.available(),
            "series": bool(self.config.indexers) and self.tmdb().available(),
            "advisor": adv.Advisor(self.config.advisor, self.ctx.http).available(),
        }

    # --- catalog ----------------------------------------------------------------------

    def disk(self) -> dict:
        st = os.statvfs(self.media_dir)
        return {"free_bytes": st.f_bavail * st.f_frsize, "total_bytes": st.f_blocks * st.f_frsize}

    def _unlink(self, directory: Path, name: str | None) -> None:
        if not name:
            return
        path = (directory / name).resolve()
        if path.is_relative_to(directory.resolve()) and path.is_file():
            path.unlink()

    def _purge(self, item: dict) -> None:
        """Cancel the job, remove the derived files (video, poster, subtitles) and the row."""
        if item["status"] in ACTIVE:
            self.worker.cancel(item["id"])
        self._unlink(self.media_dir, item.get("file"))
        self._unlink(self.posters_dir, item.get("poster"))
        for name in (item.get("subtitles") or {}).values():
            self._unlink(self.media_dir, name)
        self.db.delete_media(item["id"])

    def delete(self, item_id: str) -> None:
        item = self.db.get_media(item_id)
        if not item:
            raise LibraryError(404, "unknown media id")
        for child in self.db.list_media(parent_id=item_id):  # a series' episodes and packs
            self._purge(child)
        self._purge(item)

    def delete_season(self, show_id: str, season: int) -> int:
        removed = 0
        for child in self.db.list_media(parent_id=show_id):
            in_pack = any(t.get("season") == season for t in child.get("targets") or [])
            if child.get("season") == season or in_pack:
                self._purge(child)
                removed += 1
        return removed

    def cancel(self, item_id: str) -> None:
        if not self.db.get_media(item_id):
            raise LibraryError(404, "unknown media id")
        self.worker.cancel(item_id)

    def retry(self, item_id: str) -> None:
        item = self.db.get_media(item_id)
        if not item or item["status"] != "error" or item["kind"] not in ("movie", "pack"):
            raise LibraryError(409, "nothing to retry")
        self.db.patch_media(item_id, {"status": "queued", "error": None})
        self.worker.enqueue(item_id)

    # --- movies -----------------------------------------------------------------------

    def search_movies(self, query: str) -> list[dict]:
        indexers = self.indexers()
        if not indexers.available():
            raise LibraryError(503, "no indexer configured")
        tmdb = self.tmdb()
        results = []
        for release in indexers.search(query):
            title, year = clean_title(release.title)
            meta = tmdb.search_movie(title, year) if tmdb.available() and title else None
            meta = meta or {}
            results.append(
                {
                    "title": meta.get("title") or title or release.title,
                    "release": release.title,
                    "year": meta.get("year") or year,
                    "tmdb_id": meta.get("tmdb_id"),
                    "imdb_id": release.imdb_id,
                    "poster_url": meta.get("poster_url"),
                    "overview": meta.get("overview"),
                    "torrent": release.to_dict(),
                }
            )
        return results

    def add_movie(
        self,
        title: str,
        year: int | None = None,
        magnet: str | None = None,
        local_file: str | None = None,
        tmdb_id: int | None = None,
        imdb_id: str | None = None,
        poster_url: str | None = None,
        overview: str | None = None,
    ) -> str:
        if not magnet and not local_file:
            raise LibraryError(400, "magnet or local_file required")
        if local_file:
            path = (self.media_dir / local_file).resolve()
            if not path.is_relative_to(self.media_dir.resolve()) or not path.is_file():
                raise LibraryError(404, "local file not found")
        movie_id = slugify(title, year)
        if self.db.get_media(movie_id):
            raise LibraryError(409, "already in the library")
        poster = None
        if poster_url and self.tmdb().download(poster_url, self.posters_dir / f"{movie_id}.jpg"):
            poster = f"{movie_id}.jpg"
        self.db.upsert_media(
            {
                "id": movie_id,
                "kind": "movie",
                "title": title,
                "year": year,
                "status": "queued",
                "file": f"{movie_id}.mp4",
                "added_at": now(),
                "tmdb_id": tmdb_id,
                "imdb_id": imdb_id,
                "overview": overview,
                "poster": poster,
                "magnet": magnet,
                "local_source": local_file,
                "subtitles": {},
                "subtitle_offsets": {},
                "progress": {"download": 0 if magnet else 1, "transcode": 0},
                "error": None,
            }
        )
        self.worker.enqueue(movie_id)
        return movie_id

    def backfill_overviews(self) -> None:
        """Movies downloaded without a synopsis get one (retried at each start)."""
        tmdb = self.tmdb()
        if not tmdb.available():
            return
        for item in self.db.list_media(kind="movie"):
            if (
                not item.get("overview")
                and item.get("tmdb_id")
                and (overview := tmdb.movie_overview(item["tmdb_id"]))
            ):
                self.db.patch_media(item["id"], {"overview": overview})

    # --- advisor ----------------------------------------------------------------------

    def recommend(self, criteria: dict, keywords: str, kind: str) -> list[dict]:
        advisor = adv.Advisor(self.config.advisor, self.ctx.http)
        if not advisor.available():
            raise LibraryError(503, "advisor not configured")
        owned = [i["title"] for i in self.db.list_media() if i["kind"] in ("movie", "series")]
        excluded = sorted({b["title"] for b in self.db.blacklist()} | set(owned))
        prompt = adv.build_prompt(criteria, excluded, keywords, kind, self.config.general.language)
        try:
            recs = advisor.recommend(prompt)
        except adv.AdvisorError as err:
            raise LibraryError(502, str(err)) from err
        tmdb = self.tmdb()
        out = []
        for rec in recs:
            title, year = rec["title"], rec.get("year")
            meta = None
            if tmdb.available():
                found = tmdb.search_tv(title, year, limit=1) if kind == "series" else None
                meta = (
                    (found[0] if found else None)
                    if kind == "series"
                    else tmdb.search_movie(title, year)
                )
            english = tmdb.english_title(meta["tmdb_id"], kind) if meta else None
            out.append(
                {
                    "id": slugify(title, year),
                    "title": title,
                    # Torrent searches work best with the English title.
                    "query": english or (meta or {}).get("original_title") or title,
                    "kind": kind,
                    "year": year,
                    "tmdb_id": (meta or {}).get("tmdb_id"),
                    "poster_url": (meta or {}).get("poster_url"),
                    "summary": adv.clip(rec.get("description")),
                }
            )
        return out

    def forget(self, title: str, year: int | None, item_id: str | None) -> dict:
        entry = {"id": item_id or slugify(title, year), "title": title, "year": year}
        self.db.blacklist_add(entry["id"], title, year, now())
        return entry
