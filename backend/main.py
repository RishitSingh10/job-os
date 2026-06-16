"""FastAPI application factory and ASGI entry point.

Run locally with::

    uv run uvicorn backend.main:app --reload

The :func:`create_app` factory keeps construction explicit and testable: tests can
build an isolated app instance without importing module-level global state.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from core.config import Settings, get_settings
from core.logging import configure_logging, get_logger
from core.paths import ensure_storage_layout
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown.

    On startup: configure logging and guarantee the storage layout exists. The
    database engine and scheduler are wired in here in their respective phases.
    """
    settings: Settings = app.state.settings
    configure_logging(settings)
    log = get_logger(__name__)

    paths = ensure_storage_layout(settings)
    log.info(
        "startup",
        app=settings.app_name,
        version=__version__,
        environment=settings.environment.value,
        storage_root=str(paths.root),
    )
    try:
        yield
    finally:
        log.info("shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a FastAPI application instance."""
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Local-first, single-user AI Job OS.",
        debug=settings.debug,
        lifespan=lifespan,
    )
    # Stash settings on app state so dependencies and lifespan share one instance.
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    return app


# Module-level ASGI app for `uvicorn backend.main:app`.
app = create_app()
