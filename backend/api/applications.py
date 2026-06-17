"""Applications router — CRUD, status transitions, and status counts."""

from __future__ import annotations

from typing import Annotated

from core.applications.service import ApplicationService
from core.database.enums import ApplicationStatus
from core.database.models import Application
from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.api.schemas.applications import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusUpdate,
    ApplicationUpdate,
    BoardColumn,
    StatusCount,
)
from backend.api.schemas.common import Message, Page

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _with_job(session: AsyncSession, application: Application) -> Application:
    """Eagerly load the ``job`` relationship so it can be serialised safely.

    After a mutation the relationship is unloaded; accessing it during response
    serialisation would otherwise trigger an (illegal) async lazy-load.
    """
    await session.refresh(application, attribute_names=["job"])
    return application


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(payload: ApplicationCreate, session: SessionDep) -> Application:
    service = ApplicationService(session)
    application = await service.create_for_job(Application(**payload.model_dump()))
    return await _with_job(session, application)


@router.get("", response_model=Page[ApplicationRead])
async def list_applications(
    session: SessionDep,
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    job_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[ApplicationRead]:
    service = ApplicationService(session)
    items, total = await service.list_applications(
        status=status_filter, job_id=job_id, tag=tag, search=search, offset=offset, limit=limit
    )
    return Page[ApplicationRead](
        items=[ApplicationRead.model_validate(a) for a in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/counts", response_model=list[StatusCount])
async def application_counts(session: SessionDep) -> list[StatusCount]:
    counts = await ApplicationService(session).counts_by_status()
    return [StatusCount(status=s, count=c) for s, c in counts.items()]


@router.get("/board", response_model=list[BoardColumn])
async def application_board(session: SessionDep) -> list[BoardColumn]:
    """Applications grouped into ordered Kanban columns."""
    columns = await ApplicationService(session).board()
    return [
        BoardColumn(
            status=status,
            count=len(items),
            items=[ApplicationRead.model_validate(a) for a in items],
        )
        for status, items in columns
    ]


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: int, session: SessionDep) -> Application:
    return await ApplicationService(session).get_or_404(application_id)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: int, payload: ApplicationUpdate, session: SessionDep
) -> Application:
    service = ApplicationService(session)
    application = await service.get_or_404(application_id)
    updated = await service.update(application, payload.model_dump(exclude_unset=True))
    return await _with_job(session, updated)


@router.put("/{application_id}/status", response_model=ApplicationRead)
async def set_application_status(
    application_id: int, payload: ApplicationStatusUpdate, session: SessionDep
) -> Application:
    service = ApplicationService(session)
    application = await service.get_or_404(application_id)
    updated = await service.set_status(application, payload.status)
    return await _with_job(session, updated)


@router.delete("/{application_id}", response_model=Message)
async def delete_application(application_id: int, session: SessionDep) -> Message:
    service = ApplicationService(session)
    application = await service.get_or_404(application_id)
    await service.delete(application)
    return Message(detail=f"Application {application_id} deleted")
