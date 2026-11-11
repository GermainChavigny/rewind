"""TV power and weather routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from rewind.context import AppContext, require
from rewind.power import PowerError, provider
from rewind.weather import WeatherUnavailable

router = APIRouter(prefix="/api")


class PowerIn(BaseModel):
    on: bool


@router.get("/tv/power")
def get_power(ctx: AppContext = Depends(require("power"))) -> dict:
    try:
        return {"on": provider(ctx.config.power, ctx.http).state()}
    except PowerError as err:
        raise HTTPException(504, str(err)) from err


@router.post("/tv/power")
def set_power(body: PowerIn, ctx: AppContext = Depends(require("power"))) -> dict:
    try:
        return {"on": provider(ctx.config.power, ctx.http).set(body.on)}
    except PowerError as err:
        raise HTTPException(504, str(err)) from err


@router.get("/weather")
def weather(request: Request, ctx: AppContext = Depends(require("weather"))) -> dict:
    try:
        return request.app.state.weather.forecast(ctx.config.weather)
    except WeatherUnavailable as err:
        raise HTTPException(503, "weather unavailable") from err
