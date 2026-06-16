"""Application service — CRUD, filtering, and status lifecycle transitions."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import select

from core.database.base import utcnow
from core.database.crud import CRUDService
from core.database.enums import ApplicationStatus
from core.database.models import Application, Job
from core.exceptions import EntityNotFoundError


class ApplicationService(CRUDService[Application]):
    model = Application

    async def create_for_job(self, application: Application) -> Application:
        """Create an application, validating that the referenced job exists."""
        job = await self.session.get(Job, application.job_id)
        if job is None:
            raise EntityNotFoundError(Job.__name__, application.job_id)
        return await self.create(application)

    async def set_status(self, application: Application, status: ApplicationStatus) -> Application:
        """Transition status, stamping ``applied_at`` the first time it's applied."""
        application.status = status
        if status == ApplicationStatus.applied and application.applied_at is None:
            application.applied_at = utcnow()
        return await self.update(application, {})

    async def list_applications(
        self,
        *,
        status: ApplicationStatus | None = None,
        job_id: int | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Application], int]:
        conditions = []
        if status is not None:
            conditions.append(Application.status == status)
        if job_id is not None:
            conditions.append(Application.job_id == job_id)
        if search:
            conditions.append(Application.notes.ilike(f"%{search}%"))  # type: ignore[attr-defined]
        return await self.list(conditions=conditions, offset=offset, limit=limit)

    async def counts_by_status(self) -> dict[ApplicationStatus, int]:
        """Per-status totals — powers the Kanban column counts and the funnel."""
        stmt = select(Application.status)
        rows = (await self.session.exec(stmt)).all()
        counts: dict[ApplicationStatus, int] = dict.fromkeys(ApplicationStatus, 0)
        for status in rows:
            counts[status] += 1
        return counts
