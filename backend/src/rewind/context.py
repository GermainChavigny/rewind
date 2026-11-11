"""Shared application context, reachable from any route through `get_ctx`."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request

from rewind.config import Config, ConfigStore
from rewind.db import Database
from rewind.paths import Paths


@dataclass
class AppContext:
    paths: Paths
    config_store: ConfigStore
    db: Database
    http: httpx.Client

    @property
    def config(self) -> Config:
        return self.config_store.get()


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def require(module_id: str):
    """Route dependency: 404 unless the module is configured."""
    from rewind.modules import MODULES

    module = MODULES[module_id]

    def dep(request: Request) -> AppContext:
        ctx = get_ctx(request)
        if not module.configured(ctx.config):
            raise HTTPException(404, f"module '{module_id}' is not configured")
        return ctx

    return dep
