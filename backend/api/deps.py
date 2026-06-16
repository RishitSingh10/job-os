"""FastAPI dependency providers.

Centralises request-scoped dependencies. ``get_app_settings`` resolves the
:class:`Settings` instance that the app was *constructed* with (stored on
``app.state``), rather than the process-global cached settings. This keeps the app
testable: ``create_app(test_settings)`` fully controls configuration for that
instance.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from core.config import Settings
from core.database import Database
from fastapi import Request
from sqlmodel.ext.asyncio.session import AsyncSession


def get_app_settings(request: Request) -> Settings:
    """Return the :class:`Settings` bound to the running application instance."""
    return request.app.state.settings


def get_database(request: Request) -> Database:
    """Return the :class:`Database` bound to the running application instance."""
    return request.app.state.db


def get_embedder(request: Request):
    """Return the app's :class:`Embedder` (always present; lazy until used)."""
    return request.app.state.embedder


def get_vector_store(request: Request):
    """Return the app's :class:`VectorStore`, or ``None`` if unavailable."""
    return request.app.state.vector_store


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a transactional :class:`AsyncSession` for the duration of a request.

    Commits on success and rolls back on error (handled by ``Database.session``).
    """
    db: Database = request.app.state.db
    async with db.session() as session:
        yield session
