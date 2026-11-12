"""
Virtual remote (the phone page at /remote/) and the TV page's side of it.

No PIN: the remote does what the physical remote does, from the local network.
The TV reports what it shows (`PUT /api/tv/report`); the phones follow it on
`/api/remote/events` to switch between the TV and the movies layout and to
open the phone keyboard when the TV waits for text.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from rewind import system
from rewind.context import AppContext
from rewind.power import PowerError, provider

log = logging.getLogger(__name__)

remote = APIRouter(prefix="/api/remote")
tv = APIRouter(prefix="/api/tv")

Mode = Literal["tv", "movies"]
MODES: tuple[Mode, ...] = ("tv", "movies")
# Keys of the virtual remote that are not keymap actions.
HOME = "home"  # leave the movies: back to the REWIND welcome screen
MACHINE = "machine_power"  # turn the computer off
LAYOUT_KV = {"tv": "remote_layout", "movies": "remote_layout.movies"}
# The "end of broadcast" card stays this long on the TV before it goes dark.
SHUTDOWN_CARD_S = 4.0

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def _extra_actions(ctx: AppContext) -> list[str]:
    return [HOME] + ([MACHINE] if ctx.config.system.shutdown != "none" else [])


def _publish_tv(request: Request, event: dict) -> bool:
    return request.app.state.events.publish(event) > 0


# --- keys -----------------------------------------------------------------------------


class PressIn(BaseModel):
    action: str = Field(pattern="^[a-z0-9_]{1,40}$")


@remote.post("/press")
def press(body: PressIn, request: Request) -> dict:
    if body.action not in _ctx(request).config.remote.keys and body.action != HOME:
        raise HTTPException(404, "unknown remote action")
    return {"delivered": _publish_tv(request, {"type": "action", "action": body.action})}


# --- touchpad and phone keyboard (movies mode) ------------------------------------------


class PointerIn(BaseModel):
    # Finger movement on the phone's pad, in phone pixels (the TV scales it).
    dx: float = Field(default=0, ge=-2000, le=2000)
    dy: float = Field(default=0, ge=-2000, le=2000)
    click: bool = False
    scroll: float = Field(default=0, ge=-5000, le=5000)


@remote.post("/pointer")
def pointer(body: PointerIn, request: Request) -> dict:
    return {"delivered": _publish_tv(request, {"type": "pointer", **body.model_dump()})}


class TextIn(BaseModel):
    text: str = Field(max_length=200)
    submit: bool = False


@remote.post("/text")
def text(body: TextIn, request: Request) -> dict:
    """Text typed on the phone, for the field being edited on the TV."""
    return {"delivered": _publish_tv(request, {"type": "text", **body.model_dump()})}


# --- the computer's power -----------------------------------------------------------------


@remote.post("/shutdown")
def shutdown(request: Request) -> dict:
    """Shows the end-of-broadcast card, then turns the TV and the computer off."""
    ctx = _ctx(request)
    mode = ctx.config.system.shutdown
    if mode == "none":
        raise HTTPException(404, "shutdown disabled")
    state = request.app.state
    events = state.events
    events.publish({"type": "shutdown"})

    def run() -> None:
        time.sleep(SHUTDOWN_CARD_S)
        if not state.poweroff(mode):
            events.publish({"type": "shutdown_failed"})
            state.remote_events.publish({"type": "error", "message": "shutdown_failed"})
            return
        # The computer stops in a few seconds: switch the TV's plug off meanwhile.
        plug = provider(ctx.config.power, ctx.http)
        if plug:
            try:
                plug.set(False)
            except PowerError as err:
                log.warning("TV left on at shutdown: %s", err)

    threading.Thread(target=run, name="shutdown", daemon=True).start()
    return {"started": True, "delay_s": SHUTDOWN_CARD_S}


# --- layouts (one per mode, saved on the TV) -----------------------------------------------


@remote.get("/layout")
def layout(request: Request) -> dict:
    ctx = _ctx(request)
    keys = ctx.config.remote.keys
    return {
        "actions": list(keys),
        "extra": _extra_actions(ctx),
        "layouts": {mode: ctx.db.get_kv(LAYOUT_KV[mode], None) for mode in MODES},
    }


class LayoutIn(BaseModel):
    cols: int = Field(ge=2, le=6)
    rows: int = Field(ge=2, le=14)
    cells: dict[str, int]


@remote.put("/layout/{mode}")
def save_layout(mode: Mode, body: LayoutIn, request: Request) -> dict:
    ctx = _ctx(request)
    known = set(ctx.config.remote.keys) | set(_extra_actions(ctx))
    size = body.cols * body.rows
    cells = {a: i for a, i in body.cells.items() if a in known and 0 <= i < size}
    if len(set(cells.values())) != len(cells):
        raise HTTPException(422, "two buttons on the same cell")
    saved = {"cols": body.cols, "rows": body.rows, "cells": cells}
    ctx.db.set_kv(LAYOUT_KV[mode], saved)
    return saved


# --- what the TV shows ------------------------------------------------------------------------


class KeyboardState(BaseModel):
    text: str = Field(default="", max_length=200)
    # What the text is for: a film search, a series search, the advisor's keywords.
    purpose: Literal["movie", "series", "advisor"] = "movie"


class TvReport(BaseModel):
    mode: Mode = "tv"
    keyboard: KeyboardState | None = None


def _state(request: Request) -> dict:
    report: TvReport | None = request.app.state.tv_report
    listening = request.app.state.events.listeners > 0
    return {
        "type": "state",
        "listening": listening,
        **(report or TvReport()).model_dump(),
    }


@tv.put("/report")
def report(body: TvReport, request: Request) -> dict:
    """The TV page tells what it shows (sent on every change)."""
    request.app.state.tv_report = body
    request.app.state.remote_events.publish(_state(request))
    return {"ok": True}


@remote.get("/events")
async def remote_events(request: Request) -> StreamingResponse:
    """Server-Sent Events for the phone remotes: the TV's state, then its changes."""
    return StreamingResponse(
        request.app.state.remote_events.stream(first=_state(request)),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@tv.get("/events")
async def tv_events(request: Request) -> StreamingResponse:
    """Server-Sent Events for the TV page (virtual remote, sync test, chimes)."""
    return StreamingResponse(
        request.app.state.events.stream(), media_type="text/event-stream", headers=SSE_HEADERS
    )


@remote.get("/admin-url")
def admin_url(request: Request) -> dict:
    """The settings page's address from a phone on the same network (QR code on the TV)."""
    ip = system.lan_address()
    port = request.url.port
    host = ip or request.url.hostname or "localhost"
    return {"url": f"http://{host}{f':{port}' if port else ''}/admin/", "lan": ip is not None}
