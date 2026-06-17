"""Tailoring router — generate and read tailored resumes."""

from __future__ import annotations

from typing import Annotated

from agents.tailoring import TailoredResumeService, TailoringAgent
from core.embeddings import Embedder
from core.llm import LLMClient
from core.paths import StoragePaths
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_embedder, get_llm, get_session, get_storage
from backend.api.schemas.common import Page
from backend.api.schemas.tailoring import TailoredResumeRead, TailorRequest, TailorResult

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LLMDep = Annotated[LLMClient, Depends(get_llm)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
StorageDep = Annotated[StoragePaths, Depends(get_storage)]


@router.post("/tailor", response_model=TailorResult)
async def tailor_resume(
    req: TailorRequest,
    session: SessionDep,
    llm: LLMDep,
    embedder: EmbedderDep,
    storage: StorageDep,
) -> TailorResult:
    """Generate a truthful, ATS-optimized resume version for a job."""
    agent = TailoringAgent(session, llm, embedder=embedder, storage=storage)
    outcome = await agent.tailor(
        base_resume_id=req.base_resume_id, job_id=req.job_id, exports=req.exports
    )
    resume = outcome.tailored
    delta = round((resume.score_after or 0.0) - (resume.score_before or 0.0), 2)
    return TailorResult(
        resume=TailoredResumeRead.model_validate(resume),
        truthful=outcome.truthful,
        introduced_skills=outcome.introduced_skills,
        score_delta=delta,
    )


@router.get("/tailored", response_model=Page[TailoredResumeRead])
async def list_tailored(
    session: SessionDep,
    job_id: int | None = None,
    base_resume_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[TailoredResumeRead]:
    items, total = await TailoredResumeService(session).list_for(
        job_id=job_id, base_resume_id=base_resume_id, offset=offset, limit=limit
    )
    return Page[TailoredResumeRead](
        items=[TailoredResumeRead.model_validate(t) for t in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/tailored/{tailored_id}", response_model=TailoredResumeRead)
async def get_tailored(tailored_id: int, session: SessionDep):
    return await TailoredResumeService(session).get_or_404(tailored_id)
