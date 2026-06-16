"""Scoring router — run ATS scoring and read past scores."""

from __future__ import annotations

from typing import Annotated

from agents.ats import ATSAgent, ATSScoreService
from core.database.models import ATSScore
from core.embeddings import Embedder
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_embedder, get_session
from backend.api.schemas.common import Page
from backend.api.schemas.scoring import ATSScoreRead, ScoreRequest

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


@router.post("/score", response_model=ATSScoreRead)
async def score_resume(req: ScoreRequest, session: SessionDep, embedder: EmbedderDep) -> ATSScore:
    """Score a resume against a job (weighted keyword/skills/experience/education/semantic)."""
    agent = ATSAgent(session, embedder=embedder)
    return await agent.score(job_id=req.job_id, resume_id=req.resume_id)


@router.get("/scores", response_model=Page[ATSScoreRead])
async def list_scores(
    session: SessionDep,
    job_id: int | None = None,
    resume_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[ATSScoreRead]:
    items, total = await ATSScoreService(session).list_scores(
        job_id=job_id, resume_id=resume_id, offset=offset, limit=limit
    )
    return Page[ATSScoreRead](
        items=[ATSScoreRead.model_validate(s) for s in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/scores/{score_id}", response_model=ATSScoreRead)
async def get_score(score_id: int, session: SessionDep) -> ATSScore:
    return await ATSScoreService(session).get_or_404(score_id)
