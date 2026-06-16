"""Generic async CRUD service base.

``CRUDService`` provides the repetitive create/read/update/delete/list+count
operations for any SQLModel table, so domain services only add the queries that
are actually specific to them (filtering, status transitions, dedup, ...).

It is constructed with a live :class:`AsyncSession`; flushing (not committing) is
used so the surrounding request-scoped transaction — opened by the ``get_session``
dependency — controls the commit boundary.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.exceptions import EntityNotFoundError

# Upper bound on page size to protect the single-user box from accidental huge scans.
MAX_LIMIT = 200


class CRUDService[ModelT: SQLModel]:
    """Reusable async CRUD operations for one model type."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def get_or_404(self, obj_id: int) -> ModelT:
        obj = await self.get(obj_id)
        if obj is None:
            raise EntityNotFoundError(self.model.__name__, obj_id)
        return obj

    async def count(self, *conditions: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(self.model)
        for condition in conditions:
            stmt = stmt.where(condition)
        result = await self.session.exec(stmt)
        return int(result.one())

    async def list(
        self,
        *,
        conditions: Sequence[ColumnElement[bool]] = (),
        order_by: ColumnElement[Any] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[ModelT], int]:
        """Return a page of rows plus the total count matching the conditions."""
        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)

        stmt = select(self.model)
        for condition in conditions:
            stmt = stmt.where(condition)
        stmt = stmt.order_by(order_by if order_by is not None else self.model.id.desc())  # type: ignore[attr-defined]
        stmt = stmt.offset(offset).limit(limit)

        items = (await self.session.exec(stmt)).all()
        total = await self.count(*conditions)
        return items, total

    async def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, db_obj: ModelT, data: dict[str, Any]) -> ModelT:
        """Apply a partial update (only provided keys) and persist."""
        for key, value in data.items():
            setattr(db_obj, key, value)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelT) -> None:
        await self.session.delete(db_obj)
        await self.session.flush()
