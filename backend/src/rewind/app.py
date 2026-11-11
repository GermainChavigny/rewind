"""FastAPI application: API + (later) the built frontend, on a single port."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rewind import __version__
from rewind.config import ConfigStore
from rewind.context import AppContext
from rewind.db import Database
from rewind.library.service import LibraryService
from rewind.paths import Paths
from rewind.routes import admin, core, devices, library
from rewind.weather import WeatherService

log = logging.getLogger(__name__)


def create_app(
    paths: Paths | None = None, http: httpx.Client | None = None, start_jobs: bool = True
) -> FastAPI:
    paths = (paths or Paths.from_env()).ensure()
    http = http or httpx.Client(headers={"User-Agent": f"rewind/{__version__}"})
    ctx = AppContext(
        paths=paths,
        config_store=ConfigStore(paths.config / "config.toml"),
        db=Database(paths.data / "rewind.db"),
        http=http,
    )

    library_service = LibraryService(ctx)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("REWIND %s — data: %s, config: %s", __version__, paths.data, paths.config)
        if ctx.config.library.enabled and start_jobs:
            library_service.start()
        yield
        http.close()

    app = FastAPI(title="REWIND", version=__version__, lifespan=lifespan)
    app.state.ctx = ctx
    app.state.weather = WeatherService(http)
    app.state.library = library_service

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    for module in (core, devices, library, admin):
        app.include_router(module.router)

    # The built TV UI (frontend/dist), served on the same port as the API.
    dist = frontend_dir()
    if dist and (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    else:
        log.warning("frontend not built (%s): only the API is served", dist)
    return app


def frontend_dir() -> Path | None:
    if env := os.environ.get("REWIND_FRONTEND_DIR"):
        return Path(env)
    # Source checkout: <repo>/backend/src/rewind/app.py → <repo>/frontend/dist
    return Path(__file__).resolve().parents[3] / "frontend" / "dist"
