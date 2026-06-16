"""Resumes router — CRUD with filtering and pagination.

File upload + parsing is added in Phase 7; this exposes the resume library records.
"""

from __future__ import annotations

from typing import Annotated

from core.database.models import Resume
from core.resumes.service import ResumeService
from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.api.schemas.common import Message, Page
from backend.api.schemas.resumes import ResumeCreate, ResumeRead, ResumeUpdate

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(payload: ResumeCreate, session: SessionDep) -> Resume:
    service = ResumeService(session)
    resume = Resume(**payload.model_dump())
    return await service.create(resume)


@router.get("", response_model=Page[ResumeRead])
async def list_resumes(
    session: SessionDep,
    is_base: bool | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[ResumeRead]:
    service = ResumeService(session)
    items, total = await service.list_resumes(
        is_base=is_base, search=search, offset=offset, limit=limit
    )
    return Page[ResumeRead](
        items=[ResumeRead.model_validate(r) for r in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(resume_id: int, session: SessionDep) -> Resume:
    return await ResumeService(session).get_or_404(resume_id)


@router.patch("/{resume_id}", response_model=ResumeRead)
async def update_resume(resume_id: int, payload: ResumeUpdate, session: SessionDep) -> Resume:
    service = ResumeService(session)
    resume = await service.get_or_404(resume_id)
    return await service.update(resume, payload.model_dump(exclude_unset=True))


@router.delete("/{resume_id}", response_model=Message)
async def delete_resume(resume_id: int, session: SessionDep) -> Message:
    service = ResumeService(session)
    resume = await service.get_or_404(resume_id)
    await service.delete(resume)
    return Message(detail=f"Resume {resume_id} deleted")
