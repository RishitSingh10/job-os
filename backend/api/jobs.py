"""Jobs router — CRUD with filtering and pagination."""

from __future__ import annotations

from typing import Annotated

from core.database.enums import JobSource
from core.database.models import Job
from core.jobs.dedup import make_dedup_hash
from core.jobs.service import JobService
from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.api.schemas.common import Message, Page
from backend.api.schemas.jobs import JobCreate, JobRead, JobUpdate

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, session: SessionDep) -> Job:
    """Create a job (or return the existing one if its fingerprint matches)."""
    service = JobService(session)
    job = Job(
        **payload.model_dump(),
        dedup_hash=make_dedup_hash(title=payload.title, company=payload.company, url=payload.url),
    )
    stored, _created = await service.upsert(job)
    return stored


@router.get("", response_model=Page[JobRead])
async def list_jobs(
    session: SessionDep,
    source: JobSource | None = None,
    company: str | None = None,
    easy_apply: bool | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[JobRead]:
    service = JobService(session)
    items, total = await service.list_jobs(
        source=source,
        company=company,
        easy_apply=easy_apply,
        search=search,
        offset=offset,
        limit=limit,
    )
    return Page[JobRead](
        items=[JobRead.model_validate(j) for j in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, session: SessionDep) -> Job:
    return await JobService(session).get_or_404(job_id)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(job_id: int, payload: JobUpdate, session: SessionDep) -> Job:
    service = JobService(session)
    job = await service.get_or_404(job_id)
    return await service.update(job, payload.model_dump(exclude_unset=True))


@router.delete("/{job_id}", response_model=Message)
async def delete_job(job_id: int, session: SessionDep) -> Message:
    service = JobService(session)
    job = await service.get_or_404(job_id)
    await service.delete(job)
    return Message(detail=f"Job {job_id} deleted")
