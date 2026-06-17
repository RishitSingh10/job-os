"""Cover Letter Agent — generate concise / startup / enterprise style letters."""

from __future__ import annotations

from core.database.crud import CRUDService
from core.database.enums import CoverLetterStyle, DocumentFormat
from core.database.models import CoverLetter
from core.documents import export, extension_for
from core.jobs.service import JobService
from core.llm import LLMClient, LLMUsageService
from core.logging import get_logger
from core.paths import StoragePaths
from core.resumes.service import ResumeService
from sqlmodel import func, select

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are an expert cover-letter writer. Write a compelling, specific cover letter "
    "grounded ONLY in the candidate's real resume — never invent experience, "
    "employers, or skills. Address the role and company directly. Return only the "
    "letter body as plain text; no placeholders like [Your Name] beyond a sign-off."
)

_STYLE_GUIDANCE = {
    CoverLetterStyle.concise: (
        "Style: concise. 3 short paragraphs, under ~200 words, direct and confident."
    ),
    CoverLetterStyle.startup: (
        "Style: startup. Energetic, first-person, mission-driven; emphasize ownership, "
        "speed, and impact; relaxed but professional tone."
    ),
    CoverLetterStyle.enterprise: (
        "Style: enterprise. Formal and structured; emphasize reliability, scale, "
        "process, and measurable results; polished business tone."
    ),
}


def build_cover_letter_prompt(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    style: CoverLetterStyle,
) -> str:
    return (
        f"# Role\n{job_title} at {company}\n\n"
        f"# Job description\n{job_description}\n\n"
        f"# Candidate resume (only source of truth)\n{resume_text}\n\n"
        f"# Instructions\n{_STYLE_GUIDANCE[style]}\n"
        "Write the cover letter now."
    )


class CoverLetterService(CRUDService[CoverLetter]):
    model = CoverLetter

    async def next_version(self, *, job_id: int, style: CoverLetterStyle) -> int:
        stmt = (
            select(func.count())
            .select_from(CoverLetter)
            .where(CoverLetter.job_id == job_id, CoverLetter.style == style)
        )
        return int((await self.session.exec(stmt)).one()) + 1

    async def list_for(self, *, job_id: int | None = None, offset: int = 0, limit: int = 50):
        conditions = [CoverLetter.job_id == job_id] if job_id is not None else []
        return await self.list(conditions=conditions, offset=offset, limit=limit)


class CoverLetterAgent:
    """Generate truthful, style-specific cover letters."""

    def __init__(self, session, llm: LLMClient, *, storage: StoragePaths | None = None) -> None:
        self.session = session
        self.llm = llm
        self.jobs = JobService(session)
        self.resumes = ResumeService(session)
        self.letters = CoverLetterService(session)
        self.usage = LLMUsageService(session)
        self.storage = storage or StoragePaths.from_settings()

    async def generate(
        self,
        *,
        job_id: int,
        resume_id: int,
        style: CoverLetterStyle = CoverLetterStyle.concise,
        exports: list[DocumentFormat] | None = None,
    ) -> CoverLetter:
        job = await self.jobs.get_or_404(job_id)
        resume = await self.resumes.get_or_404(resume_id)

        prompt = build_cover_letter_prompt(
            resume.content, job.title, job.company, job.description, style
        )
        result = await self.llm.generate(prompt, system=SYSTEM_PROMPT, temperature=0.5)
        await self.usage.record(result, operation="cover_letter", job_id=job.id)

        content = result.text.strip()
        version = await self.letters.next_version(job_id=job_id, style=style)
        letter = await self.letters.create(
            CoverLetter(
                job_id=job.id,
                resume_id=resume.id,
                style=style,
                version=version,
                content=content,
                model_used=self.llm.model,
            )
        )

        if exports:
            await self._export(letter, exports)

        log.info("cover_letter_generated", job_id=job.id, style=str(style), version=version)
        return letter

    async def _export(self, letter: CoverLetter, formats: list[DocumentFormat]) -> None:
        title = f"Cover Letter ({letter.style.value})"
        field_map = {
            DocumentFormat.pdf: "pdf_path",
            DocumentFormat.docx: "docx_path",
            DocumentFormat.markdown: "markdown_path",
        }
        updates: dict[str, str] = {}
        for fmt in formats:
            if fmt not in field_map:  # cover letters don't persist an HTML path column
                continue
            filename = f"cover_{letter.id}_v{letter.version}.{extension_for(fmt)}"
            path = export(
                letter.content,
                fmt=fmt,
                path=self.storage.cover_letters / filename,
                title=title,
            )
            updates[field_map[fmt]] = str(path)
        if updates:
            await self.letters.update(letter, updates)
