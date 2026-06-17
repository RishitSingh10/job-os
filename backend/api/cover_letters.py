"""Cover letters router — generate and read cover letters."""

from __future__ import annotations

from typing import Annotated

from agents.cover_letter import CoverLetterAgent, CoverLetterService
from core.database.models import CoverLetter
from core.llm import LLMClient
from core.paths import StoragePaths
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_llm, get_session, get_storage
from backend.api.schemas.common import Page
from backend.api.schemas.cover_letters import CoverLetterRead, CoverLetterRequest

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LLMDep = Annotated[LLMClient, Depends(get_llm)]
StorageDep = Annotated[StoragePaths, Depends(get_storage)]


@router.post("", response_model=CoverLetterRead)
async def create_cover_letter(
    req: CoverLetterRequest, session: SessionDep, llm: LLMDep, storage: StorageDep
) -> CoverLetter:
    agent = CoverLetterAgent(session, llm, storage=storage)
    return await agent.generate(
        job_id=req.job_id, resume_id=req.resume_id, style=req.style, exports=req.exports
    )


@router.get("", response_model=Page[CoverLetterRead])
async def list_cover_letters(
    session: SessionDep,
    job_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[CoverLetterRead]:
    items, total = await CoverLetterService(session).list_for(
        job_id=job_id, offset=offset, limit=limit
    )
    return Page[CoverLetterRead](
        items=[CoverLetterRead.model_validate(c) for c in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{cover_letter_id}", response_model=CoverLetterRead)
async def get_cover_letter(cover_letter_id: int, session: SessionDep) -> CoverLetter:
    return await CoverLetterService(session).get_or_404(cover_letter_id)
