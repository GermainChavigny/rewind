"""Core routes: modules, channels, YouTube progress, display state, alarm."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from rewind.context import AppContext, get_ctx, require
from rewind.modules import module_states

router = APIRouter(prefix="/api")


@router.get("/modules")
def modules(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return module_states(ctx.config)


@router.get("/ui")
def ui(ctx: AppContext = Depends(get_ctx)) -> dict:
    """Settings the TV UI needs at boot (no secrets)."""
    c = ctx.config
    return {
        "language": c.general.language,
        "keymap": c.remote.keys,
        "alarm": c.alarm.model_dump(),
        "crt_effects": c.display.crt_effects,
    }


@router.get("/channels")
def channels(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    """Channels in remote order; `number` is the remote key (1–9)."""
    return [{"number": i, **ch.model_dump()} for i, ch in enumerate(ctx.config.channels, start=1)]


# --- YouTube progress -----------------------------------------------------------


class ProgressIn(BaseModel):
    video_id: str = Field(min_length=1)
    video_index: int = Field(ge=0)
    position: float = Field(ge=0)


@router.get("/progress/{playlist_id}")
def get_progress(playlist_id: str, ctx: AppContext = Depends(require("channels"))) -> dict:
    return ctx.db.get_playlist_progress(playlist_id) or {}


@router.put("/progress/{playlist_id}")
def put_progress(
    playlist_id: str, body: ProgressIn, ctx: AppContext = Depends(require("channels"))
) -> dict:
    # A validated body is never empty: the v1 "empty state overwrites progress"
    # failure mode cannot happen here.
    ctx.db.save_playlist_progress(playlist_id, body.video_id, body.video_index, body.position)
    return {"status": "ok"}


# --- Display state (persisted across reloads) -------------------------------------


class StatePatch(BaseModel):
    darkness: float | None = Field(default=None, ge=0, le=1)  # black veil opacity
    volume: float | None = Field(default=None, ge=0, le=100)  # player volume


STATE_DEFAULTS = {"darkness": 0.0, "volume": 100.0}


@router.get("/state")
def get_state(ctx: AppContext = Depends(get_ctx)) -> dict:
    return {k: ctx.db.get_kv(f"state.{k}", v) for k, v in STATE_DEFAULTS.items()}


@router.patch("/state")
def patch_state(body: StatePatch, ctx: AppContext = Depends(get_ctx)) -> dict:
    for key, value in body.model_dump(exclude_none=True).items():
        ctx.db.set_kv(f"state.{key}", value)
    return get_state(ctx)


# --- Alarm --------------------------------------------------------------------------


class Alarm(BaseModel):
    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    enabled: bool


ALARM_DEFAULT = {"time": "08:00", "enabled": False}


@router.get("/alarm")
def get_alarm(ctx: AppContext = Depends(require("alarm"))) -> dict:
    return ctx.db.get_kv("alarm", ALARM_DEFAULT)


@router.put("/alarm")
def put_alarm(body: Alarm, ctx: AppContext = Depends(require("alarm"))) -> dict:
    ctx.db.set_kv("alarm", body.model_dump())
    return body.model_dump()
