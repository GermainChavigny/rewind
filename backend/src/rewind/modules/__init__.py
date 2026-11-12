"""
Feature modules.

Each module declares whether it is configured. The TV UI asks `/api/modules`
and only shows configured features; routes of an unconfigured module answer
404 (see `context.require`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rewind.config import Config


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    configured: Callable[[Config], bool]
    description: str = ""


def _alarm_ready(c: Config) -> bool:
    # A chime alone is enough to wake up; the alarm channel is optional.
    return c.alarm.chime != "none" or any(ch.alarm for ch in c.channels)


def _power_ready(c: Config) -> bool:
    if c.power.provider == "shelly":
        return bool(c.power.shelly_host)
    return c.power.provider == "fake"


MODULES: dict[str, Module] = {
    m.id: m
    for m in [
        Module("channels", "Channels", lambda c: bool(c.channels), "YouTube playlist channels"),
        Module("alarm", "Alarm", _alarm_ready, "Progressive alarm: chime, then a channel"),
        Module("power", "TV power", _power_ready, "Turn the TV on/off via a smart plug"),
        Module(
            "weather",
            "Weather",
            lambda c: c.weather.latitude is not None and c.weather.longitude is not None,
            "Open-Meteo forecast",
        ),
        Module("library", "Library", lambda c: c.library.enabled, "Movies and series"),
    ]
}


def module_states(config: Config) -> list[dict]:
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "configured": m.configured(config),
        }
        for m in MODULES.values()
    ]
