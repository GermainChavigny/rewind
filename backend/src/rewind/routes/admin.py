"""
Admin API, used by the phone admin UI. Protected by an optional PIN
(`[admin] pin`), sent in the `X-Rewind-Pin` header.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import ValidationError

from rewind.config import Config, masked, restore_secrets
from rewind.context import AppContext, get_ctx

router = APIRouter(prefix="/api/admin")


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
