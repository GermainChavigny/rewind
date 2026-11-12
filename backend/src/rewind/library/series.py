"""
Series: TMDB gives the season/episode structure, the indexers the torrents,
the job worker downloads and maps files to episodes.

Hybrid acquisition — every acquisition is a `pack` job:
  episode — search "Show SxxEyy" → pack with one target.
  season  — search the "Show Sxx" pack → targets every episode of the season;
            episodes missing from the pack fall back to single-episode searches.
  series  — the season flow, for each season.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

from rewind.db import Database, now
from rewind.library.jobs import ACTIVE, JobWorker, episode_id
from rewind.library.sources import CAT_TV, Indexers, Tmdb, slugify

log = logging.getLogger(__name__)

WATCHED_THRESHOLD = 0.92
AIRING = ("Returning Series", "In Production")


class SeriesManager:
    def __init__(
        self,
        db: Database,
        worker: JobWorker,
        posters_dir: Path,
        tmdb: Callable[[], Tmdb],
        indexers: Callable[[], Indexers],
    ):
        self.db = db
        self.worker = worker
        self.posters_dir = posters_dir
        # Factories: the clients follow the live config (keys can change any time).
        self._tmdb = tmdb
        self._indexers = indexers
        self._notices: dict[str, tuple[float, str | None]] = {}
        worker.on_pack_missing = self._fallback

    @property
    def tmdb(self) -> Tmdb:
        return self._tmdb()

    @property
    def indexers(self) -> Indexers:
        return self._indexers()

    # --- catalog ----------------------------------------------------------------------

    def add_show(self, tmdb_id: int) -> dict | None:
        details = self.tmdb.tv_details(tmdb_id)
        if not details:
            return None
        show_id = slugify(details["title"], details.get("year"))
        existing = self.db.get_media(show_id)
        poster = (existing or {}).get("poster")
        if not poster and self.tmdb.download(
            details.get("poster_url"), self.posters_dir / f"{show_id}.jpg"
        ):
            poster = f"{show_id}.jpg"
        show = {
            **(existing or {}),
            "id": show_id,
            "kind": "series",
            "title": details["title"],
            "year": details.get("year"),
            "status": "ready",  # a catalog entry, not a job
            "added_at": (existing or {}).get("added_at") or now(),
            "tmdb_id": details["tmdb_id"],
            "original_title": details.get("original_title"),
            "overview": details.get("overview"),
            "poster": poster,
            "tmdb_status": details.get("tmdb_status"),
            "number_of_seasons": details.get("number_of_seasons"),
            "seasons": details.get("seasons") or [],
            "last_checked_at": now(),
        }
        self.db.upsert_media(show)
        return show

    def recheck_airing(self) -> None:
        """Refresh the seasons of shows still on the air (new episodes)."""
        for show in self.db.list_media(kind="series"):
            if show.get("tmdb_status") not in AIRING or not show.get("tmdb_id"):
                continue
            details = self.tmdb.tv_details(show["tmdb_id"])
            if details:
                self.db.patch_media(
                    show["id"],
                    {
                        "tmdb_status": details.get("tmdb_status"),
                        "number_of_seasons": details.get("number_of_seasons"),
                        "seasons": details.get("seasons") or [],
                        "last_checked_at": now(),
                    },
                )

    # --- downloads --------------------------------------------------------------------

    def download_async(
        self, show_id: str, scope: str, season: int | None = None, episode: int | None = None
    ) -> None:
        """Searches can take a while (a whole series): run them in the background."""
        self._notice(show_id, "searching")

        def run() -> None:
            try:
                queued, errors = self.download(show_id, scope, season, episode)
            except Exception as err:  # noqa: BLE001 - never silent
                log.warning("series download %s failed: %s", show_id, err)
                self._notice(show_id, "search_failed")
                return
            self._notice(show_id, None if queued else ("no_source" if not errors else errors[0]))

        threading.Thread(target=run, daemon=True, name=f"series-{show_id}").start()

    def download(
        self, show_id: str, scope: str, season: int | None = None, episode: int | None = None
    ) -> tuple[list[str], list[str]]:
        show = self.db.get_media(show_id)
        if not show or show["kind"] != "series":
            raise ValueError("unknown series")
        title = self._search_title(show)
        queued: list[str] = []
        errors: list[str] = []
        if scope == "episode":
            s, e = int(season or 0), int(episode or 0)
            target = {"season": s, "episode": e, "episode_id": episode_id(show_id, s, e)}
            candidates = self._candidates(f"{title} S{s:02d}E{e:02d}")
            if not candidates:
                # Single-episode releases are rare for some shows: fall back on the
                # season pack, from which only this episode's file is taken.
                candidates = self._candidates(f"{title} S{s:02d}")
                log.info("%s S%02dE%02d: no single-episode release, trying the season pack",
                         show_id, s, e)  # fmt: skip
            if candidates:
                queued.append(self._start_pack(show, candidates, [target], "episode", s))
            else:
                errors.append("no_source")
        elif scope == "season":
            s = int(season or 0)
            targets = self._season_targets(show, s)
            candidates = self._candidates(f"{title} S{s:02d}")
            if candidates and targets:
                queued.append(self._start_pack(show, candidates, targets, "season", s))
            else:  # no pack: episode by episode
                for t in targets:
                    q, err = self.download(show_id, "episode", s, t["episode"])
                    queued += q
                    errors += err
        elif scope == "series":
            for meta in show.get("seasons") or []:
                q, err = self.download(show_id, "season", meta["season_number"])
                queued += q
                errors += err
        else:
            raise ValueError(f"unknown scope {scope}")
        return queued, errors

    def _search_title(self, show: dict) -> str:
        return (
            self.tmdb.english_title(show.get("tmdb_id"), "series")
            or show.get("original_title")
            or show["title"]
        )

    def _candidates(self, query: str, top: int = 6) -> list[str]:
        """Several magnets: the worker tries the next one when a candidate is dead."""
        indexers = self.indexers
        releases = indexers.search(query, limit=25, cat=CAT_TV)
        if not releases:
            # Some releases are filed outside the TV categories: search them all.
            releases = indexers.search(query, limit=25)
        return [r.magnet for r in releases][:top]

    def _season_targets(self, show: dict, season: int) -> list[dict]:
        episodes = self.tmdb.tv_season(show["tmdb_id"], season) or []
        if not episodes:  # fall back on the episode count of the season summary
            count = next(
                (s.get("episode_count") or 0 for s in show.get("seasons") or []
                 if s.get("season_number") == season),
                0,
            )  # fmt: skip
            episodes = [{"episode": i, "title": None} for i in range(1, count + 1)]
        return [
            {
                "season": season,
                "episode": e["episode"],
                "episode_id": episode_id(show["id"], season, e["episode"]),
                "title": e.get("title"),
            }
            for e in episodes
        ]

    def _start_pack(
        self, show: dict, candidates: list[str], targets: list[dict], scope: str, season: int
    ) -> str:
        if scope == "episode":
            label = f"S{season:02d}E{targets[0]['episode']:02d}"
            pack_id = f"{show['id']}-pack-{targets[0]['episode_id']}"
        else:
            label = f"S{season:02d}"
            pack_id = f"{show['id']}-pack-s{season:02d}"
        self.db.upsert_media(
            {
                "id": pack_id,
                "kind": "pack",
                "parent_id": show["id"],
                "title": f"{show['title']} — {label}",
                "year": show.get("year"),
                "season": season,
                "status": "queued",
                "added_at": now(),
                "show_title": show["title"],
                "tmdb_id": show.get("tmdb_id"),
                "scope": scope,
                "fallback": scope != "episode",
                "candidates": candidates,
                "targets": targets,
                "progress": {},
                "error": None,
            }
        )
        self.worker.enqueue(pack_id)
        return pack_id

    def _fallback(self, pack: dict, missing: list[dict]) -> None:
        for t in missing:
            log.info("single-episode fallback: %s", t["episode_id"])
            try:
                self.download(pack["parent_id"], "episode", t["season"], t["episode"])
            except Exception as err:  # noqa: BLE001
                log.warning("fallback %s failed: %s", t["episode_id"], err)

    # --- views ------------------------------------------------------------------------

    def _notice(self, show_id: str, text: str | None) -> None:
        self._notices[show_id] = (time.time(), text)

    def notice(self, show_id: str) -> str | None:
        at, text = self._notices.get(show_id, (0, None))
        return text if time.time() - at < 60 else None

    def season_view(self, show_id: str, season: int) -> dict | None:
        """Episodes of a season with their local state: missing | downloading | ready | error."""
        show = self.db.get_media(show_id)
        if not show or show["kind"] != "series":
            return None
        children = {c["id"]: c for c in self.db.list_media(parent_id=show_id)}
        # Episodes targeted by an active pack → the pack's download progress.
        covered: dict[tuple[int, int], float] = {}
        for c in children.values():
            if c["kind"] == "pack" and c["status"] in ACTIVE:
                dl = (c.get("progress") or {}).get("download", 0)
                for t in c.get("targets") or []:
                    covered[(t["season"], t["episode"])] = dl
        tmdb_eps = self.tmdb.tv_season(show["tmdb_id"], season) if show.get("tmdb_id") else None
        if tmdb_eps is None:  # offline / no key: what we own
            tmdb_eps = sorted(
                (
                    {"episode": c["episode"], "title": c.get("episode_title"), "overview": None,
                     "still": None}
                    for c in children.values()
                    if c["kind"] == "episode" and c.get("season") == season
                ),
                key=lambda e: e["episode"],
            )  # fmt: skip
        out = []
        for e in tmdb_eps:
            n = e["episode"]
            item = children.get(episode_id(show_id, season, n))
            state, phase, progress = "missing", None, 0.0
            position = duration = 0.0
            watched = False
            if item:
                position, duration = item.get("position") or 0, item.get("duration") or 0
                watched = bool(item.get("watched")) or (
                    duration > 0 and position >= WATCHED_THRESHOLD * duration
                )
                p = item.get("progress") or {}
                st = item["status"]
                if st == "ready":
                    state, progress = "ready", 1.0
                elif st == "error":
                    state = "error"
                elif st == "transcoding":
                    state, phase, progress = "downloading", "transcoding", p.get("transcode", 0)
                elif st == "downloading":
                    state, phase, progress = "downloading", "downloading", p.get("download", 0)
                else:
                    state, phase = "downloading", st
            elif (season, n) in covered:
                state, phase, progress = "downloading", "downloading", covered[(season, n)]
            out.append(
                {
                    "episode": n,
                    "id": episode_id(show_id, season, n),
                    "title": e.get("title"),
                    "overview": e.get("overview"),
                    "still": e.get("still"),
                    "state": state,
                    "phase": phase,
                    "progress": round(progress, 3),
                    "position": round(position, 1),
                    "duration": round(duration, 1),
                    "watched": watched,
                }
            )
        return {"season": season, "episodes": out, "notice": self.notice(show_id)}
