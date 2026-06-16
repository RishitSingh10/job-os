"""Resume service — CRUD plus library queries."""

from __future__ import annotations

from collections.abc import Sequence

from core.database.crud import CRUDService
from core.database.models import Resume


class ResumeService(CRUDService[Resume]):
    model = Resume

    async def list_resumes(
        self,
        *,
        is_base: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Resume], int]:
        conditions = []
        if is_base is not None:
            conditions.append(Resume.is_base == is_base)
        if search:
            like = f"%{search}%"
            conditions.append(Resume.name.ilike(like))  # type: ignore[attr-defined]
        return await self.list(conditions=conditions, offset=offset, limit=limit)
