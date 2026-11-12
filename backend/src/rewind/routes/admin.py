"""
Admin API, used by the phone admin UI. Protected by an optional PIN
(`[admin] pin`), sent in the `X-Rewind-Pin` header.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from rewind.config import Config, masked, restore_secrets
from rewind.context import AppContext, get_ctx

router = APIRouter(prefix="/api/admin")
# The TV side of key learning (no PIN: the kiosk is on the local network only).
remote = APIRouter(prefix="/api/remote")


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
def put_config(body: dict, ctx: AppContext = Depends(check_pin)) -> dict:
    """Replace the whole config. Masked secrets sent back unchanged are kept."""
    try:
        new = Config.model_validate(body)
    except ValidationError as err:
        raise HTTPException(422, err.errors(include_url=False, include_context=False)) from err
    ctx.config_store.save(restore_secrets(new, ctx.config))
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


class LearnIn(BaseModel):
    action: str = Field(pattern="^[a-z_]{1,40}$")


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
