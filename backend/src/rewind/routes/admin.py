"""
Admin API, used by the phone admin UI. Protected by an optional PIN
(`[admin] pin`), sent in the `X-Rewind-Pin` header.
"""

from __future__ import annotations

import hmac
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from rewind import checks, hardware
from rewind.config import Config, masked, restore_secrets
from rewind.context import AppContext, get_ctx

router = APIRouter(prefix="/api/admin")
# The TV side of key learning (no PIN: the kiosk is on the local network only).
remote = APIRouter(prefix="/api/remote")

tv = APIRouter(prefix="/api/tv")


def check_pin(
    ctx: AppContext = Depends(get_ctx), x_rewind_pin: str = Header(default="")
) -> AppContext:
    pin = ctx.config.admin.pin
    if pin and not hmac.compare_digest(pin, x_rewind_pin):
        raise HTTPException(401, "wrong or missing PIN")
    return ctx


@router.get("/config")
def get_config(ctx: AppContext = Depends(check_pin)) -> dict:
    return masked(ctx.config)


@router.put("/config")
def put_config(body: dict, request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    """Replace the whole config. Masked secrets sent back unchanged are kept."""
    try:
        new = Config.model_validate(body)
    except ValidationError as err:
        raise HTTPException(422, err.errors(include_url=False, include_context=False)) from err
    old_audio = ctx.config.audio
    ctx.config_store.save(restore_secrets(new, ctx.config))
    audio = ctx.config.audio
    if audio != old_audio and audio.output_port:
        request.app.state.apply_av(audio.output_port, audio.av_offset_ms)
    return masked(ctx.config)


@router.get("/schema")
def schema(ctx: AppContext = Depends(check_pin)) -> dict:
    """JSON Schema of the config, used to build the admin forms."""
    return Config.model_json_schema()


@router.get("/status")
def status(request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    """What the setup wizard needs to know."""
    config = ctx.config
    return {
        "first_run": not ctx.db.get_kv("setup_done", False),
        "has_pin": bool(config.admin.pin),
        "channels": len(config.channels),
        "power": config.power.provider,
        "weather": config.weather.latitude is not None,
        "library": config.library.enabled,
        "version": request.app.version,
    }


@router.post("/setup/complete")
def setup_complete(ctx: AppContext = Depends(check_pin)) -> dict:
    """The wizard is finished: the admin shows the settings menu from now on."""
    ctx.db.set_kv("setup_done", True)
    return {"first_run": False}


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


@router.get("/geocode")
def geocode(q: str, ctx: AppContext = Depends(check_pin)) -> list[dict]:
    """Places matching a city name (Open-Meteo, free, no key) for the weather setup."""
    q = q.strip()
    if len(q) < 2:
        return []
    try:
        r = ctx.http.get(
            GEOCODE_URL, params={"name": q[:80], "count": 6, "language": "fr"}, timeout=8
        )
        r.raise_for_status()
        results = r.json().get("results") or []
    except (httpx.HTTPError, ValueError) as err:
        raise HTTPException(502, "geocoding unavailable") from err
    return [
        {
            "name": p["name"],
            "detail": ", ".join(x for x in (p.get("admin1"), p.get("country")) if x),
            "latitude": round(p["latitude"], 4),
            "longitude": round(p["longitude"], 4),
        }
        for p in results
        if "latitude" in p and "longitude" in p
    ]


class LearnIn(BaseModel):
    action: str = Field(pattern="^[a-z0-9_]{1,40}$")


@router.post("/learn")
def learn_start(body: LearnIn, request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    if body.action not in ctx.config.remote.keys:
        raise HTTPException(404, "unknown remote action")
    request.app.state.learner.start(body.action)
    return request.app.state.learner.status()


@router.get("/learn")
def learn_status(request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    return request.app.state.learner.status()


@router.delete("/learn")
def learn_cancel(request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    request.app.state.learner.cancel()
    return {"cancelled": True}


@remote.get("/learn")
def remote_pending(request: Request) -> dict:
    """Polled by the TV: which action is waiting for a key press, if any."""
    return {"action": request.app.state.learner.pending()}


class KeyIn(BaseModel):
    key: str


@remote.post("/learn")
def remote_offer(body: KeyIn, request: Request) -> dict:
    return {"accepted": request.app.state.learner.offer(body.key)}


# --- Checks, hardware, TV events ------------------------------------------------------


def _draft(body: dict, ctx: AppContext) -> Config:
    """The config as typed in the admin (not saved), with stored secrets put back."""
    try:
        return restore_secrets(Config.model_validate(body), ctx.config)
    except ValidationError as err:
        raise HTTPException(422, err.errors(include_url=False, include_context=False)) from err


class CheckIn(BaseModel):
    service: Literal["tmdb", "opensubtitles", "indexer", "advisor", "power"]
    index: int = 0
    config: dict


@router.post("/check")
def check(body: CheckIn, ctx: AppContext = Depends(check_pin)) -> dict:
    cfg = _draft(body.config, ctx)
    http = ctx.http
    if body.service == "tmdb":
        return checks.check_tmdb(cfg, http)
    if body.service == "opensubtitles":
        return checks.check_opensubtitles(cfg, http)
    if body.service == "power":
        return checks.check_power(cfg, http)
    items = cfg.indexers if body.service == "indexer" else cfg.advisor
    if not 0 <= body.index < len(items):
        raise HTTPException(404, "no such entry")
    if body.service == "indexer":
        return checks.check_indexer(cfg.indexers[body.index], http)
    return checks.check_advisor(cfg.advisor[body.index], http)


class ModelsIn(BaseModel):
    index: int
    config: dict


@router.post("/models")
def models(body: ModelsIn, ctx: AppContext = Depends(check_pin)) -> list[str]:
    cfg = _draft(body.config, ctx)
    if not 0 <= body.index < len(cfg.advisor):
        raise HTTPException(404, "no such provider")
    try:
        return checks.list_models(cfg.advisor[body.index], ctx.http)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as err:
        raise HTTPException(502, "models unavailable") from err


@router.get("/hardware")
def hardware_info(ctx: AppContext = Depends(check_pin)) -> dict:
    """Video outputs/modes and audio output ports of the TV computer."""
    return {"displays": hardware.displays(), "audio": hardware.audio_ports()}


class OffsetIn(BaseModel):
    port: str = Field(pattern=r"^[\w.-]{1,80}$")
    ms: int = Field(ge=-2000, le=2000)


@router.post("/av-offset")
def av_offset(body: OffsetIn, request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    """Applies an A/V offset now, without saving (live tuning during the sync test)."""
    return {"applied": request.app.state.apply_av(body.port, body.ms)}


class TvEventIn(BaseModel):
    type: Literal["avtest", "avtest_stop", "chime", "chime_stop"]
    chime: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,20}$")


@router.post("/tv-event")
def tv_event(body: TvEventIn, request: Request, ctx: AppContext = Depends(check_pin)) -> dict:
    """Asks the TV to run the A/V sync test or play an alarm chime."""
    event = body.model_dump(exclude_none=True)
    return {"delivered": request.app.state.events.publish(event)}


# --- Virtual remote (no PIN: it does what the physical remote does) ----------------------


class PressIn(BaseModel):
    action: str = Field(pattern="^[a-z0-9_]{1,40}$")


@remote.post("/press")
def remote_press(body: PressIn, request: Request) -> dict:
    ctx: AppContext = request.app.state.ctx
    if body.action not in ctx.config.remote.keys:
        raise HTTPException(404, "unknown remote action")
    return {
        "delivered": request.app.state.events.publish({"type": "action", "action": body.action})
    }


@remote.get("/layout")
def remote_layout(request: Request) -> dict:
    ctx: AppContext = request.app.state.ctx
    keys = ctx.config.remote.keys
    return {
        "actions": list(keys),
        "keys": keys,
        "layout": ctx.db.get_kv("remote_layout", None),
    }


class LayoutIn(BaseModel):
    cols: int = Field(ge=2, le=6)
    rows: int = Field(ge=3, le=14)
    cells: dict[str, int]


@remote.put("/layout")
def save_remote_layout(body: LayoutIn, request: Request) -> dict:
    ctx: AppContext = request.app.state.ctx
    size = body.cols * body.rows
    cells = {a: i for a, i in body.cells.items() if a in ctx.config.remote.keys and 0 <= i < size}
    if len(set(cells.values())) != len(cells):
        raise HTTPException(422, "two buttons on the same cell")
    layout = {"cols": body.cols, "rows": body.rows, "cells": cells}
    ctx.db.set_kv("remote_layout", layout)
    return layout


@tv.get("/events")
async def tv_events(request: Request) -> StreamingResponse:
    """Server-Sent Events for the TV page (virtual remote, sync test, chimes)."""
    return StreamingResponse(
        request.app.state.events.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
