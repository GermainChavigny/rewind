"""Weather from Open-Meteo (free, no key), shaped for the retro weather screens."""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx

from rewind.config import WeatherConfig

log = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"
CACHE_S = 15 * 60
# Day periods of the forecast popup: (id, end hour, hour shown). Morning runs to noon.
PERIODS = [("morning", 12, 9), ("afternoon", 18, 15), ("evening", 24, 21)]


def upcoming_periods(local_now: datetime, count: int = 3) -> list[tuple[str, int, datetime]]:
    """The next `count` periods, the current one first: (id, day offset, hour to show).

    In the evening this is tonight, then tomorrow morning and afternoon; at
    night (before 6) today's morning comes first. A period already under way
    shows the coming hour, not the one gone by.
    """
    today = local_now.replace(minute=0, second=0, microsecond=0)
    out: list[tuple[str, int, datetime]] = []
    for offset in (0, 1):
        day = today.replace(hour=0) + timedelta(days=offset)
        for period_id, end, shown in PERIODS:
            if day + timedelta(hours=end) <= local_now:
                continue  # already over
            at = day + timedelta(hours=shown)
            if at <= local_now:
                at = min(today + timedelta(hours=1), day + timedelta(hours=end - 1))
            out.append((period_id, offset, at))
            if len(out) == count:
                return out
    return out


class WeatherUnavailable(Exception):
    pass


class WeatherService:
    def __init__(self, http: httpx.Client):
        self.http = http
        self._lock = threading.Lock()
        self._cache: dict[tuple, tuple[float, dict]] = {}

    def forecast(self, cfg: WeatherConfig) -> dict:
        key = (cfg.latitude, cfg.longitude)
        with self._lock:
            cached = self._cache.get(key)
            if cached and time.time() - cached[0] < CACHE_S:
                return cached[1]
        try:
            data = self._fetch(cfg)
        except (httpx.HTTPError, KeyError, ValueError, IndexError) as err:
            log.warning("weather unavailable: %s", err)
            if cached:  # stale is better than nothing
                return cached[1]
            raise WeatherUnavailable(str(err)) from err
        with self._lock:
            self._cache[key] = (time.time(), data)
        return data

    def _fetch(self, cfg: WeatherConfig) -> dict:
        r = self.http.get(
            URL,
            params={
                "latitude": cfg.latitude,
                "longitude": cfg.longitude,
                "hourly": "weather_code,temperature_2m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",  # times come back in the location's local time
                "forecast_days": 2,
            },
            timeout=8,
        )
        r.raise_for_status()
        payload = r.json()
        hourly = payload["hourly"]
        times, codes, temps = hourly["time"], hourly["weather_code"], hourly["temperature_2m"]
        local_now = datetime.now(UTC) + timedelta(seconds=payload.get("utc_offset_seconds", 0))

        def index_at(dt: datetime) -> int:
            stamp = dt.strftime("%Y-%m-%dT%H:00")
            return times.index(stamp) if stamp in times else 0

        # Header icon: next hour.
        idx = index_at(local_now + timedelta(hours=1))
        periods = []
        for period_id, offset, at in upcoming_periods(local_now):
            i = index_at(at)
            periods.append(
                {"id": period_id, "day": offset, "code": codes[i], "temp": round(temps[i])}
            )
        # The day summary follows the panels: tomorrow's once most of them are tomorrow.
        day = 1 if sum(p["day"] for p in periods) * 2 > len(periods) else 0
        daily = payload.get("daily", {})

        def daily_at(name: str, fallback: float) -> float:
            values = daily.get(name) or []
            return values[day] if len(values) > day else fallback

        return {
            "location": cfg.location_name,
            "code": codes[idx],
            "hour": times[idx][11:16],
            "day": {
                "offset": day,
                "code": daily_at("weather_code", codes[idx]),
                "hi": round(daily_at("temperature_2m_max", temps[idx])),
                "lo": round(daily_at("temperature_2m_min", temps[idx])),
            },
            "periods": periods,
        }
