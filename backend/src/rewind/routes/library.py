"""
Library routes: catalog and playback state, media files, search, downloads,
series and the Movie Advisor. Everything answers 404 when the library module
is disabled; search, series and advisor answer 503 when not configured.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from rewind.context import AppContext, require
from rewind.library.service import LibraryError, LibraryService

router = APIRouter()

WATCHED_THRESHOLD = 0.92  # fraction of the duration after which an item counts as watched

MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".vtt": "text/vtt",
}


def _safe_child(base: Path, name: str) -> Path:
    """Resolve `name` inside `base`, refusing any path traversal."""
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()):
        raise HTTPException(400, "invalid path")
    return path


def service(request: Request, ctx: AppContext = Depends(require("library"))) -> LibraryService:
    return request.app.state.library


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LibraryError as err:
        raise HTTPException(err.status, str(err)) from err


# --- catalog ---------------------------------------------------------------------------


@router.get("/api/library")
def library(
    kind: str | None = None,
    parent: str | None = None,
    ctx: AppContext = Depends(require("library")),
) -> list[dict]:
    return ctx.db.list_media(kind=kind, parent_id=parent)


@router.get("/api/library/features")
def features(lib: LibraryService = Depends(service)) -> dict:
    return lib.features()


@router.get("/api/library/disk")
def disk(lib: LibraryService = Depends(service)) -> dict:
    return lib.disk()


@router.get("/api/library/jobs")
def jobs(lib: LibraryService = Depends(service)) -> dict:
    """Unfinished jobs, polled by the UI while something downloads."""
    return lib.worker.active_jobs()


@router.get("/api/library/{media_id}")
def library_item(media_id: str, ctx: AppContext = Depends(require("library"))) -> dict:
    item = ctx.db.get_media(media_id)
    if not item:
        raise HTTPException(404, "unknown media id")
    return item


@router.delete("/api/library/{media_id}")
def delete_item(media_id: str, lib: LibraryService = Depends(service)) -> dict:
    """Remove an item and its files (a series: with all its episodes)."""
    _run(lib.delete, media_id)
    return {"deleted": media_id}


@router.post("/api/library/{media_id}/cancel")
def cancel(media_id: str, lib: LibraryService = Depends(service)) -> dict:
    _run(lib.cancel, media_id)
    return {"cancelled": media_id}


@router.post("/api/library/{media_id}/retry")
def retry(media_id: str, lib: LibraryService = Depends(service)) -> dict:
    _run(lib.retry, media_id)
    return {"queued": media_id}


class PlaybackIn(BaseModel):
    position: float | None = Field(default=None, ge=0)
    duration: float | None = Field(default=None, ge=0)
    watched: bool | None = None
    started: bool | None = None  # playback started: stamps last_played_at
    subtitle_mode: str | None = Field(default=None, pattern="^([a-z]{2}|off)$")
    subtitle_offsets: dict[str, float] | None = None  # per language, seconds
    audio_track: int | None = Field(default=None, ge=0)
    fit: str | None = Field(default=None, pattern="^(contain|cover)$")


@router.patch("/api/library/{media_id}/playback")
def playback(
    media_id: str, body: PlaybackIn, ctx: AppContext = Depends(require("library"))
) -> dict:
    item = ctx.db.get_media(media_id)
    if not item:
        raise HTTPException(404, "unknown media id")
    fields = body.model_dump(exclude_none=True)
    if fields.pop("started", False) or "position" in fields:
        fields["last_played_at"] = int(time.time())
    if "position" in fields:
        duration = fields.get("duration") or item.get("duration") or 0
        if (
            "watched" not in fields
            and duration
            and fields["position"] / duration >= WATCHED_THRESHOLD
        ):
            fields["watched"] = True
    return ctx.db.patch_media(media_id, fields)


@router.get("/api/posters/{media_id}")
def poster(media_id: str, ctx: AppContext = Depends(require("library"))) -> FileResponse:
    item = ctx.db.get_media(media_id)
    name = (item or {}).get("poster")
    if item and not name and item.get("parent_id"):  # episode → its series' poster
        name = (ctx.db.get_media(item["parent_id"]) or {}).get("poster")
    if not name:
        raise HTTPException(404, "poster not found")
    path = _safe_child(ctx.paths.data / "posters", name)
    if not path.is_file():
        raise HTTPException(404, "poster not found")
    return FileResponse(path)


@router.get("/media/{name:path}")
def media_file(name: str, ctx: AppContext = Depends(require("library"))) -> FileResponse:
    """Videos and subtitles, with HTTP Range support (seeking)."""
    path = _safe_child(ctx.paths.media, name)
    if not path.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(path, media_type=MEDIA_TYPES.get(path.suffix.lower()))


# --- search & downloads ----------------------------------------------------------------


class QueryIn(BaseModel):
    query: str = Field(min_length=1, max_length=200)


@router.post("/api/library/search")
def search(body: QueryIn, lib: LibraryService = Depends(service)) -> list[dict]:
    return _run(lib.search_movies, body.query.strip())


class ProbeItem(BaseModel):
    hash: str
    magnet: str
    seeders: int = 0


class ProbeIn(BaseModel):
    items: list[ProbeItem] = Field(max_length=100)


@router.post("/api/library/probe")
def probe(body: ProbeIn, lib: LibraryService = Depends(service)) -> dict:
    """Start reachability probes (most seeded first)."""
    lib.prober.submit([i.model_dump() for i in body.items])
    return {"count": len(body.items)}


@router.get("/api/library/probe/status")
def probe_status(
    hashes: str = Query(default=""), lib: LibraryService = Depends(service)
) -> dict[str, str]:
    """reachable | unreachable | pending | unknown, per hash."""
    return lib.prober.status([h for h in hashes.split(",") if h])


class DownloadIn(BaseModel):
    title: str = Field(min_length=1)
    year: int | None = None
    magnet: str | None = None
    local_file: str | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None
    poster_url: str | None = None
    overview: str | None = None


@router.post("/api/library/download")
def download(body: DownloadIn, lib: LibraryService = Depends(service)) -> dict:
    return {"id": _run(lib.add_movie, **body.model_dump())}


# --- series ----------------------------------------------------------------------------


@router.post("/api/series/search")
def series_search(body: QueryIn, lib: LibraryService = Depends(service)) -> list[dict]:
    tmdb = lib.tmdb()
    if not tmdb.available():
        raise HTTPException(503, "TMDB is not configured")
    return tmdb.search_tv(body.query.strip())


class AddShowIn(BaseModel):
    tmdb_id: int


@router.post("/api/series")
def series_add(body: AddShowIn, lib: LibraryService = Depends(service)) -> dict:
    if not lib.tmdb().available():
        raise HTTPException(503, "TMDB is not configured")
    show = lib.series.add_show(body.tmdb_id)
    if not show:
        raise HTTPException(404, "series not found on TMDB")
    return show


@router.get("/api/series/{show_id}/season/{season}")
def series_season(show_id: str, season: int, lib: LibraryService = Depends(service)) -> dict:
    view = lib.series.season_view(show_id, season)
    if view is None:
        raise HTTPException(404, "unknown series")
    return view


class SeriesDownloadIn(BaseModel):
    scope: str = Field(pattern="^(episode|season|series)$")
    season: int | None = None
    episode: int | None = None


@router.post("/api/series/{show_id}/download")
def series_download(
    show_id: str, body: SeriesDownloadIn, lib: LibraryService = Depends(service)
) -> dict:
    """Searches run in the background; the season view reports the outcome (notice)."""
    show = lib.db.get_media(show_id)
    if not show or show["kind"] != "series":
        raise HTTPException(404, "unknown series")
    if not lib.indexers().available():
        raise HTTPException(503, "no indexer configured")
    lib.series.download_async(show_id, body.scope, body.season, body.episode)
    return {"status": "searching"}


@router.delete("/api/series/{show_id}/season/{season}")
def series_delete_season(show_id: str, season: int, lib: LibraryService = Depends(service)) -> dict:
    return {"removed": lib.delete_season(show_id, season)}


# --- advisor ---------------------------------------------------------------------------


class RecommendIn(BaseModel):
    criteria: dict[str, str] = Field(default_factory=dict)
    keywords: str = Field(default="", max_length=200)
    kind: str = Field(default="movie", pattern="^(movie|series)$")


@router.post("/api/advisor/recommend")
def recommend(body: RecommendIn, lib: LibraryService = Depends(service)) -> list[dict]:
    return _run(lib.recommend, body.criteria, body.keywords, body.kind)


class ForgetIn(BaseModel):
    title: str = Field(min_length=1)
    year: int | None = None
    id: str | None = None


@router.post("/api/advisor/forget")
def forget(body: ForgetIn, lib: LibraryService = Depends(service)) -> dict:
    return lib.forget(body.title, body.year, body.id)
