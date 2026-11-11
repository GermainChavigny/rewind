"""FastAPI application: API + (later) the built frontend, on a single port."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from rewind import __version__
from rewind.config import ConfigStore
from rewind.context import AppContext
from rewind.db import Database
from rewind.paths import Paths
from rewind.routes import admin, core, devices, library
from rewind.weather import WeatherService

log = logging.getLogger(__name__)


def create_app(paths: Paths | None = None, http: httpx.Client | None = None) -> FastAPI:
    paths = (paths or Paths.from_env()).ensure()
    http = http or httpx.Client(headers={"User-Agent": f"rewind/{__version__}"})
    ctx = AppContext(
        paths=paths,
        config_store=ConfigStore(paths.config / "config.toml"),
        db=Database(paths.data / "rewind.db"),
        http=http,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("REWIND %s — data: %s, config: %s", __version__, paths.data, paths.config)
        yield
        http.close()

    app = FastAPI(title="REWIND", version=__version__, lifespan=lifespan)
    app.state.ctx = ctx
    app.state.weather = WeatherService(http)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    for module in (core, devices, library, admin):
        app.include_router(module.router)
    return app
