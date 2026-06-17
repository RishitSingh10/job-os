"""Unit tests for the Tailoring Agent."""

from __future__ import annotations

from agents.tailoring import TailoringAgent
from core.config import Settings
from core.database import Database
from core.database.enums import DocumentFormat, JobSource, ResumeFileType
from core.database.models import Job, Resume
from core.embeddings import DeterministicEmbedder
from core.llm import StubLLMClient
from core.paths import StoragePaths

JD = "Senior Python Engineer with FastAPI, Docker, and AWS. 5+ years required."
BASE = "Experienced engineer skilled in Python and FastAPI. 6 years building APIs."


async def _seed(session) -> tuple[int, int]:
    job = Job(
        title="Senior Python Engineer",
        company="Acme",
        url="https://acme.com/1",
        source=JobSource.manual,
        dedup_hash="acme:py",
        description=JD,
    )
    resume = Resume(
        name="Base",
        file_type=ResumeFileType.pdf,
        source_filename="cv.pdf",
        file_path="/tmp/cv.pdf",
        content=BASE,
    )
    session.add(job)
    session.add(resume)
    await session.flush()
    return job.id, resume.id


async def test_tailor_produces_diff_scores_and_version(db: Database) -> None:
    # Stub returns a truthful rewrite (only base skills, reworded).
    tailored_text = "Summary: Python and FastAPI engineer with 6 years building APIs."
    async with db.session() as session:
        job_id, resume_id = await _seed(session)
        agent = TailoringAgent(
            session, StubLLMClient(text=tailored_text), embedder=DeterministicEmbedder()
        )
        first = await agent.tailor(base_resume_id=resume_id, job_id=job_id)
        second = await agent.tailor(base_resume_id=resume_id, job_id=job_id)

    assert first.tailored.version == 1
    assert second.tailored.version == 2
    assert first.tailored.content == tailored_text
    assert first.tailored.diff  # non-empty unified diff
    assert first.tailored.score_before is not None
    assert first.tailored.score_after is not None
    assert first.truthful is True
    assert first.introduced_skills == []


async def test_truthfulness_audit_flags_introduced_skills(db: Database) -> None:
    # Stub fabricates a skill not present in the base resume.
    async with db.session() as session:
        job_id, resume_id = await _seed(session)
        agent = TailoringAgent(
            session,
            StubLLMClient(text="Python, FastAPI, and expert Kubernetes and Rust skills."),
            embedder=DeterministicEmbedder(),
        )
        outcome = await agent.tailor(base_resume_id=resume_id, job_id=job_id)

    assert outcome.truthful is False
    assert "kubernetes" in outcome.introduced_skills
    assert "rust" in outcome.introduced_skills


async def test_tailor_exports_files(db: Database, settings: Settings) -> None:
    storage = StoragePaths.from_settings(settings).ensure()
    async with db.session() as session:
        job_id, resume_id = await _seed(session)
        agent = TailoringAgent(
            session,
            StubLLMClient(text="Python FastAPI engineer."),
            embedder=DeterministicEmbedder(),
            storage=storage,
        )
        outcome = await agent.tailor(
            base_resume_id=resume_id,
            job_id=job_id,
            exports=[DocumentFormat.markdown, DocumentFormat.pdf],
        )

    tr = outcome.tailored
    assert tr.markdown_path and tr.pdf_path
    from pathlib import Path

    assert Path(tr.markdown_path).exists()
    assert Path(tr.pdf_path).exists()


async def test_records_llm_usage(db: Database) -> None:
    from core.llm import LLMUsageService

    async with db.session() as session:
        job_id, resume_id = await _seed(session)
        agent = TailoringAgent(session, StubLLMClient(text="x"), embedder=DeterministicEmbedder())
        await agent.tailor(base_resume_id=resume_id, job_id=job_id)
        items, total = await LLMUsageService(session).list()

    assert total == 1
    assert items[0].operation == "tailor"
