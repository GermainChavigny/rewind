"""FastAPI application: API + (later) the built frontend, on a single port."""

from __future__ import annotations

from fastapi import FastAPI

from rewind import __version__
from rewind.paths import Paths


def create_app(paths: Paths | None = None) -> FastAPI:
    paths = (paths or Paths.from_env()).ensure()
    app = FastAPI(title="REWIND", version=__version__)
    app.state.paths = paths

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app
