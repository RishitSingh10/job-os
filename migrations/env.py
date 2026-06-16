"""Alembic migration environment (async, SQLModel-aware).

The target metadata is ``SQLModel.metadata``; importing :mod:`core.database.models`
registers every table on it. The database URL comes from the application settings,
so migrations always target the same database the app uses.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

import core.database.models  # noqa: F401  (registers tables on SQLModel.metadata)
from alembic import context
from core.config import get_settings
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata
_settings = get_settings()


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL)."""
    context.configure(
        url=_settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite-safe ALTER via batch mode
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the async engine."""
    engine = create_async_engine(_settings.database_url, future=True)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
