"""Tailoring Agent — produce a truthful, job-specific resume version.

Pipeline: score the base resume against the job (to surface gaps) → prompt the LLM
to rewrite truthfully for ATS fit → re-score the result → compute a unified diff →
audit for fabricated skills → persist a versioned :class:`TailoredResume` and,
optionally, export it to PDF/DOCX/Markdown/HTML.

Truthfulness is enforced two ways: a strict system prompt, and a post-hoc audit
that flags any skill keyword present in the tailored text but absent from the base.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff

from core.database.crud import CRUDService
from core.database.enums import DocumentFormat
from core.database.models import TailoredResume
from core.documents import export, extension_for
from core.embeddings import Embedder
from core.jobs.service import JobService
from core.llm import LLMClient, LLMUsageService
from core.logging import get_logger
from core.paths import StoragePaths
from core.resumes.service import ResumeService
from sqlmodel import func, select

from agents.ats.agent import ATSAgent
from agents.ats.skills import extract_skills

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are an expert resume writer optimizing a resume for a specific job and for "
    "ATS keyword matching. CRITICAL RULES: Never invent experience, employers, "
    "dates, education, or skills the candidate does not already have. Only rephrase, "
    "reorder, and emphasize what is truthfully present in the base resume. You may "
    "surface relevant existing experience and mirror the job's terminology, but do "
    "not fabricate. Return only the rewritten resume as plain text with clear "
    "section headings; no commentary."
)


def build_tailor_prompt(
    resume_text: str,
    job_title: str,
    job_description: str,
    missing_keywords: list[str],
    missing_skills: list[str],
) -> str:
    gaps = ", ".join(list(dict.fromkeys([*missing_skills, *missing_keywords]))[:20]) or "none"
    return (
        f"# Target role\n{job_title}\n\n"
        f"# Job description\n{job_description}\n\n"
        f"# Keywords/skills the resume is currently missing (add ONLY if truthful)\n{gaps}\n\n"
        "# Base resume (the only source of truth — do not add anything not here)\n"
        f"{resume_text}\n\n"
        "Rewrite the base resume tailored to the target role: sharpen the summary, "
        "reorder and emphasize the most relevant skills and bullet points, and mirror "
        "the role's language where truthful. Keep it concise and ATS-friendly."
    )


@dataclass
class TailoringOutcome:
    """Result of a tailoring run."""

    tailored: TailoredResume
    introduced_skills: list[str]
    truthful: bool


class TailoredResumeService(CRUDService[TailoredResume]):
    model = TailoredResume

    async def next_version(self, *, job_id: int, base_resume_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(TailoredResume)
            .where(
                TailoredResume.job_id == job_id,
                TailoredResume.base_resume_id == base_resume_id,
            )
        )
        return int((await self.session.exec(stmt)).one()) + 1

    async def list_for(
        self,
        *,
        job_id: int | None = None,
        base_resume_id: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ):
        conditions = []
        if job_id is not None:
            conditions.append(TailoredResume.job_id == job_id)
        if base_resume_id is not None:
            conditions.append(TailoredResume.base_resume_id == base_resume_id)
        return await self.list(conditions=conditions, offset=offset, limit=limit)


class TailoringAgent:
    """Generate a truthful, ATS-optimized resume version for a job."""

    def __init__(
        self,
        session,
        llm: LLMClient,
        *,
        embedder: Embedder | None = None,
        storage: StoragePaths | None = None,
    ) -> None:
        self.session = session
        self.llm = llm
        self.jobs = JobService(session)
        self.resumes = ResumeService(session)
        self.tailored = TailoredResumeService(session)
        self.usage = LLMUsageService(session)
        self.ats = ATSAgent(session, embedder=embedder)
        self.storage = storage or StoragePaths.from_settings()

    async def tailor(
        self,
        *,
        base_resume_id: int,
        job_id: int,
        exports: list[DocumentFormat] | None = None,
    ) -> TailoringOutcome:
        resume = await self.resumes.get_or_404(base_resume_id)
        job = await self.jobs.get_or_404(job_id)
        job_text = ATSAgent.job_text(job)

        before = await self.ats.evaluate(resume.content, job_text)
        prompt = build_tailor_prompt(
            resume.content,
            job.title,
            job.description,
            before.missing_keywords,
            before.missing_skills,
        )
        result = await self.llm.generate(prompt, system=SYSTEM_PROMPT, temperature=0.3)
        await self.usage.record(result, operation="tailor", job_id=job.id)

        tailored_text = result.text.strip() or resume.content
        after = await self.ats.evaluate(tailored_text, job_text)

        diff = "\n".join(
            unified_diff(
                resume.content.splitlines(),
                tailored_text.splitlines(),
                fromfile="base",
                tofile="tailored",
                lineterm="",
            )
        )
        introduced = sorted(extract_skills(tailored_text) - extract_skills(resume.content))

        version = await self.tailored.next_version(job_id=job_id, base_resume_id=base_resume_id)
        tailored = await self.tailored.create(
            TailoredResume(
                job_id=job.id,
                base_resume_id=resume.id,
                version=version,
                content=tailored_text,
                diff=diff,
                score_before=before.overall,
                score_after=after.overall,
                model_used=self.llm.model,
            )
        )

        if exports:
            await self._export(tailored, exports)

        log.info(
            "resume_tailored",
            job_id=job.id,
            base_resume_id=resume.id,
            version=version,
            score_before=before.overall,
            score_after=after.overall,
            truthful=not introduced,
        )
        return TailoringOutcome(
            tailored=tailored, introduced_skills=introduced, truthful=not introduced
        )

    async def _export(self, tailored: TailoredResume, formats: list[DocumentFormat]) -> None:
        title = f"Resume v{tailored.version}"
        updates: dict[str, str] = {}
        field_map = {
            DocumentFormat.pdf: "pdf_path",
            DocumentFormat.docx: "docx_path",
            DocumentFormat.markdown: "markdown_path",
            DocumentFormat.html: "html_path",
        }
        for fmt in formats:
            filename = f"resume_{tailored.id}_v{tailored.version}.{extension_for(fmt)}"
            path = export(
                tailored.content,
                fmt=fmt,
                path=self.storage.tailored_resumes / filename,
                title=title,
            )
            updates[field_map[fmt]] = str(path)
        if updates:
            await self.tailored.update(tailored, updates)
