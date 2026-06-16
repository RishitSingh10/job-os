"""Shared pytest fixtures.

Tests run against an isolated :class:`Settings` instance pointed at a temporary
storage root, so they never touch the developer's real ``storage/`` tree or
``jobos.db``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from backend.main import create_app
from core.config import Environment, Settings
from core.logging import reset_logging_for_tests
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[Settings]:
    """Test settings with storage redirected into a tmp dir and an in-memory DB."""
    reset_logging_for_tests()
    yield Settings(
        environment=Environment.test,
        debug=True,
        storage_root=tmp_path / "storage",
        chroma_dir=tmp_path / "storage" / "chroma",
        database_url="sqlite+aiosqlite:///:memory:",
        log_json=True,
    )
    reset_logging_for_tests()


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """An httpx client bound to the ASGI app, with lifespan events executed."""
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac
