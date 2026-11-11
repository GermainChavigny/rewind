"""
Library routes (read side + playback state). Search, downloads and series
management come in phase 3.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from rewind.context import AppContext, require

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


@router.get("/api/library")
def library(
    kind: str | None = None,
    parent: str | None = None,
    ctx: AppContext = Depends(require("library")),
) -> list[dict]:
    return ctx.db.list_media(kind=kind, parent_id=parent)


@router.get("/api/library/{media_id}")
def library_item(media_id: str, ctx: AppContext = Depends(require("library"))) -> dict:
    item = ctx.db.get_media(media_id)
    if not item:
        raise HTTPException(404, "unknown media id")
    return item


class PlaybackIn(BaseModel):
    position: float | None = Field(default=None, ge=0)
    duration: float | None = Field(default=None, ge=0)
    watched: bool | None = None
    subtitle_mode: str | None = None  # "fr" | "en" | "off"
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
    if "position" in fields:
        fields["last_played_at"] = int(time.time())
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
