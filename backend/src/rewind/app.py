"""FastAPI application: API + (later) the built frontend, on a single port."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rewind import __version__, hardware, system
from rewind.config import ConfigStore
from rewind.context import AppContext
from rewind.db import Database
from rewind.events import EventBus
from rewind.learn import KeyLearner
from rewind.library.service import LibraryService
from rewind.paths import Paths
from rewind.routes import admin, core, devices, library, remote
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
    library_service.start_jobs = start_jobs

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("REWIND %s — data: %s, config: %s", __version__, paths.data, paths.config)
        if ctx.config.library.enabled:
            library_service.start()
        yield
        http.close()

    app = FastAPI(title="REWIND", version=__version__, lifespan=lifespan)
    app.state.ctx = ctx
    app.state.weather = WeatherService(http)
    app.state.library = library_service
    app.state.learner = KeyLearner()
    app.state.events = EventBus()  # to the TV page
    app.state.remote_events = EventBus()  # to the phone remotes
    app.state.tv_report = None  # what the TV shows (routes/remote.py)
    app.state.apply_av = hardware.apply_av_offset
    app.state.apply_display = hardware.apply_display
    app.state.poweroff = system.poweroff  # replaced in tests: never turn the box off
    # Settings saved but only applied at the next start (e.g. no X display).
    app.state.restart_needed = set()

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    for module in (core, devices, library, admin):
        app.include_router(module.router)
    app.include_router(admin.remote)
    app.include_router(remote.remote)
    app.include_router(remote.tv)

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
