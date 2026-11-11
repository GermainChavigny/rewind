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
# Day periods shown in the forecast popup (local hour).
PERIODS = [("morning", 9), ("afternoon", 15), ("evening", 21)]


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
        for period_id, hour in PERIODS:
            i = index_at(local_now.replace(hour=hour))
            periods.append({"id": period_id, "code": codes[i], "temp": round(temps[i])})
        daily = payload.get("daily", {})
        return {
            "location": cfg.location_name,
            "code": codes[idx],
            "hour": times[idx][11:16],
            "day": {
                "code": (daily.get("weather_code") or [codes[idx]])[0],
                "hi": round((daily.get("temperature_2m_max") or [temps[idx]])[0]),
                "lo": round((daily.get("temperature_2m_min") or [temps[idx]])[0]),
            },
            "periods": periods,
        }
