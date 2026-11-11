"""TV power providers. The TV is plugged into a smart plug."""

from __future__ import annotations

import logging

import httpx

from rewind.config import PowerConfig

log = logging.getLogger(__name__)


class PowerError(Exception):
    pass


class ShellyPower:
    """Shelly Gen2+ plug, local RPC API (no cloud, no key)."""

    def __init__(self, http: httpx.Client, host: str, switch_id: int = 0):
        self.http = http
        self.base = f"http://{host}/rpc"
        self.switch_id = switch_id

    def set(self, on: bool) -> bool:
        try:
            r = self.http.get(
                f"{self.base}/Switch.Set",
                params={"id": self.switch_id, "on": "true" if on else "false"},
                timeout=5,
            )
            r.raise_for_status()
        except httpx.HTTPError as err:
            raise PowerError(f"Shelly unreachable: {err}") from err
        return on

    def state(self) -> bool:
        try:
            r = self.http.get(
                f"{self.base}/Switch.GetStatus", params={"id": self.switch_id}, timeout=5
            )
            r.raise_for_status()
            return bool(r.json()["output"])
        except (httpx.HTTPError, KeyError, ValueError) as err:
            raise PowerError(f"Shelly unreachable: {err}") from err


class FakePower:
    """In-memory plug, for development without hardware."""

    _on = True

    def set(self, on: bool) -> bool:
        FakePower._on = on
        log.info("fake TV power: %s", "on" if on else "off")
        return on

    def state(self) -> bool:
        return FakePower._on


def provider(cfg: PowerConfig, http: httpx.Client) -> ShellyPower | FakePower | None:
    if cfg.provider == "shelly" and cfg.shelly_host:
        return ShellyPower(http, cfg.shelly_host, cfg.shelly_switch_id)
    if cfg.provider == "fake":
        return FakePower()
    return None
