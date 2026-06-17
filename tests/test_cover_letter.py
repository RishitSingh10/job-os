"""Unit tests for the Cover Letter Agent."""

from __future__ import annotations

from agents.cover_letter import CoverLetterAgent
from core.database import Database
from core.database.enums import CoverLetterStyle, JobSource, ResumeFileType
from core.database.models import Job, Resume
from core.llm import StubLLMClient


async def _seed(session) -> tuple[int, int]:
    job = Job(
        title="Backend Engineer",
        company="Globex",
        url="https://g.co/1",
        source=JobSource.manual,
        dedup_hash="g:be",
        description="Python backend role.",
    )
    resume = Resume(
        name="Base",
        file_type=ResumeFileType.pdf,
        source_filename="cv.pdf",
        file_path="/tmp/cv.pdf",
        content="Python engineer, 5 years.",
    )
    session.add(job)
    session.add(resume)
    await session.flush()
    return job.id, resume.id


async def test_generate_persists_letter_with_style(db: Database) -> None:
    async with db.session() as session:
        job_id, resume_id = await _seed(session)
        agent = CoverLetterAgent(session, StubLLMClient(text="Dear Hiring Manager, ..."))
        letter = await agent.generate(
            job_id=job_id, resume_id=resume_id, style=CoverLetterStyle.startup
        )

    assert letter.id is not None
    assert letter.style is CoverLetterStyle.startup
    assert letter.version == 1
    assert letter.content == "Dear Hiring Manager, ..."
    assert letter.model_used == "stub"


async def test_versions_increment_per_style(db: Database) -> None:
    async with db.session() as session:
        job_id, resume_id = await _seed(session)
        agent = CoverLetterAgent(session, StubLLMClient(text="letter"))
        a = await agent.generate(job_id=job_id, resume_id=resume_id, style=CoverLetterStyle.concise)
        b = await agent.generate(job_id=job_id, resume_id=resume_id, style=CoverLetterStyle.concise)
        c = await agent.generate(
            job_id=job_id, resume_id=resume_id, style=CoverLetterStyle.enterprise
        )

    assert (a.version, b.version) == (1, 2)
    assert c.version == 1  # different style → its own version sequence
