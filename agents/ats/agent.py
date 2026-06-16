"""ATS Agent — score a resume against a job and persist the result."""

from __future__ import annotations

from collections.abc import Sequence

from core.database.crud import CRUDService
from core.database.models import ATSScore, Job
from core.embeddings import Embedder
from core.logging import get_logger
from core.resumes.service import ResumeService
from sqlmodel import select

from agents.ats.scoring import (
    ScoreBreakdown,
    aggregate,
    build_analysis,
    cosine_similarity,
    jaccard,
    score_education,
    score_experience,
    score_keywords,
    score_skills,
)
from agents.ats.skills import content_tokens

log = get_logger(__name__)


class ATSScoreService(CRUDService[ATSScore]):
    model = ATSScore

    async def list_scores(
        self,
        *,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[ATSScore], int]:
        conditions = []
        if job_id is not None:
            conditions.append(ATSScore.job_id == job_id)
        if resume_id is not None:
            conditions.append(ATSScore.resume_id == resume_id)
        return await self.list(conditions=conditions, offset=offset, limit=limit)

    async def latest_for(self, *, job_id: int, resume_id: int) -> ATSScore | None:
        stmt = (
            select(ATSScore)
            .where(ATSScore.job_id == job_id, ATSScore.resume_id == resume_id)
            .order_by(ATSScore.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        return (await self.session.exec(stmt)).first()


class ATSAgent:
    """Evaluate resume↔job fit with weighted, deterministic + semantic scoring."""

    def __init__(self, session, *, embedder: Embedder | None = None) -> None:
        from core.jobs.service import JobService

        self.session = session
        self.jobs = JobService(session)
        self.resumes = ResumeService(session)
        self.scores = ATSScoreService(session)
        self._embedder = embedder

    @staticmethod
    def job_text(job: Job) -> str:
        return "\n".join(filter(None, [job.title, job.company, job.location, job.description]))

    async def _semantic_score(self, resume_text: str, job_text: str) -> float:
        if self._embedder is not None:
            try:
                vecs = await self._embedder.embed([resume_text, job_text])
                return round(max(0.0, cosine_similarity(vecs[0], vecs[1])) * 100.0, 2)
            except Exception as exc:  # Ollama down / model missing → lexical fallback
                log.warning("ats_semantic_fallback", error=str(exc))
        overlap = jaccard(set(content_tokens(resume_text)), set(content_tokens(job_text)))
        return round(overlap * 100.0, 2)

    async def evaluate(self, resume_text: str, job_text: str) -> ScoreBreakdown:
        keyword, kw_matched, kw_missing = score_keywords(resume_text, job_text)
        skills, sk_matched, sk_missing = score_skills(resume_text, job_text)
        experience = score_experience(resume_text, job_text)
        education = score_education(resume_text, job_text)
        semantic = await self._semantic_score(resume_text, job_text)

        breakdown = ScoreBreakdown(
            overall=aggregate(
                keyword=keyword,
                skills=skills,
                experience=experience,
                education=education,
                semantic=semantic,
            ),
            keyword=keyword,
            skills=skills,
            experience=experience,
            education=education,
            semantic=semantic,
            matched_keywords=kw_matched,
            missing_keywords=kw_missing,
            matched_skills=sk_matched,
            missing_skills=sk_missing,
        )
        build_analysis(breakdown)
        return breakdown

    async def score(self, *, job_id: int, resume_id: int) -> ATSScore:
        """Score a stored resume against a stored job and persist the result."""
        job = await self.jobs.get_or_404(job_id)
        resume = await self.resumes.get_or_404(resume_id)

        b = await self.evaluate(resume.content, self.job_text(job))
        used_embeddings = self._embedder is not None

        score = ATSScore(
            job_id=job.id,
            resume_id=resume.id,
            overall_score=b.overall,
            keyword_score=b.keyword,
            skills_score=b.skills,
            experience_score=b.experience,
            education_score=b.education,
            semantic_score=b.semantic,
            matched_keywords=b.matched_keywords,
            missing_keywords=b.missing_keywords,
            strengths=b.strengths,
            weaknesses=b.weaknesses,
            suggestions=b.suggestions,
            model_used="deterministic+embeddings" if used_embeddings else "deterministic",
        )
        saved = await self.scores.create(score)
        log.info(
            "ats_scored",
            job_id=job.id,
            resume_id=resume.id,
            overall=b.overall,
            model=score.model_used,
        )
        return saved
