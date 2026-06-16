"""Async database engine and session management.

The :class:`Database` class owns one async engine + session factory for the
lifetime of an application instance. It is constructed in the FastAPI lifespan and
stored on ``app.state.db`` (mirroring the settings DI pattern), which keeps tests
fully isolated: each test builds its own in-memory :class:`Database`.

No module-level globals — everything flows through an explicit instance.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import Settings, get_settings

# Importing the models module registers every table on SQLModel.metadata so that
# create_all() and Alembic autogenerate see the full schema.
from core.database import models as models  # noqa: F401
from core.logging import get_logger

log = get_logger(__name__)


def _engine_kwargs(database_url: str, *, echo: bool) -> dict[str, Any]:
    """Build engine kwargs, special-casing SQLite (file and in-memory)."""
    kwargs: dict[str, Any] = {"echo": echo, "future": True}
    if database_url.startswith("sqlite"):
        # aiosqlite + threads: required so the connection can move across tasks.
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            # A single shared connection so every session sees the same in-memory DB.
            kwargs["poolclass"] = StaticPool
    return kwargs


class Database:
    """Owns the async engine and session factory for one app instance."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.engine: AsyncEngine = create_async_engine(
            self._settings.database_url,
            **_engine_kwargs(self._settings.database_url, echo=self._settings.db_echo),
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def create_all(self) -> None:
        """Create any missing tables (idempotent fast-path for local dev)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        log.info("database_ready", url=self._settings.database_url)

    async def drop_all(self) -> None:
        """Drop every table (used by tests and reset scripts)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide a transactional session scope.

        Commits on success, rolls back on exception, always closes.
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        """Dispose the engine's connection pool on shutdown."""
        await self.engine.dispose()
        log.info("database_disposed")
