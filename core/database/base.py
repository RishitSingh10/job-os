"""Base model utilities and mixins for the SQLModel layer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Timezone-aware current UTC timestamp (used as the model default)."""
    return datetime.now(UTC)


def json_column(*, default_factory: Any = list) -> Any:
    """A JSON-backed column for list/dict fields.

    SQLite has no native array type, so structured list fields (keywords,
    strengths, tags, screenshot paths, ...) are stored as JSON. The Python-side
    ``default_factory`` guarantees a concrete value before flush.
    """
    return Field(default_factory=default_factory, sa_column=Column(JSON, nullable=False))


class TimestampMixin(SQLModel):
    """Adds ``created_at`` / ``updated_at`` audit columns.

    ``updated_at`` is bumped automatically on UPDATE via the SQLAlchemy
    ``onupdate`` hook.
    """

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": utcnow},
    )
