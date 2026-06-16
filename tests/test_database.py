"""Tests for the database layer: schema creation, CRUD, relationships, cascades."""

from __future__ import annotations

from datetime import datetime

import pytest
from core.database import Database
from core.database.enums import (
    ApplicationStatus,
    ApprovalState,
    CoverLetterStyle,
    JobSource,
    ResumeFileType,
)
from core.database.models import (
    Application,
    ApprovalWorkflow,
    ATSScore,
    CoverLetter,
    Job,
    Resume,
    TailoredResume,
)
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

EXPECTED_TABLES = {
    "resumes",
    "jobs",
    "ats_scores",
    "tailored_resumes",
    "cover_letters",
    "applications",
    "approval_workflows",
    "automation_runs",
    "llm_usage",
}


def test_metadata_registers_all_tables() -> None:
    assert EXPECTED_TABLES.issubset(set(SQLModel.metadata.tables.keys()))


async def _make_job(session: AsyncSession, **overrides: object) -> Job:
    job = Job(
        title=overrides.get("title", "Senior AI Engineer"),  # type: ignore[arg-type]
        company=overrides.get("company", "Acme"),  # type: ignore[arg-type]
        url=overrides.get("url", "https://jobs.acme.com/1"),  # type: ignore[arg-type]
        source=JobSource.linkedin,
        dedup_hash=overrides.get("dedup_hash", "acme:senior-ai-engineer"),  # type: ignore[arg-type]
    )
    session.add(job)
    await session.flush()
    return job


async def test_create_job_sets_timestamps(session: AsyncSession) -> None:
    job = await _make_job(session)
    assert job.id is not None
    assert isinstance(job.created_at, datetime)
    assert isinstance(job.updated_at, datetime)
    assert job.easy_apply is False
    assert job.source is JobSource.linkedin


async def test_resume_json_sections_default_and_roundtrip(db: Database) -> None:
    async with db.session() as session:
        resume = Resume(
            name="Base CV",
            file_type=ResumeFileType.pdf,
            source_filename="cv.pdf",
            file_path="/tmp/cv.pdf",
            content="Experienced engineer",
            sections=[{"heading": "Summary", "text": "..."}],
        )
        session.add(resume)
        await session.flush()
        resume_id = resume.id

    async with db.session() as session:
        loaded = await session.get(Resume, resume_id)
        assert loaded is not None
        assert loaded.sections == [{"heading": "Summary", "text": "..."}]
        assert loaded.is_base is True


async def test_application_relationships_navigate(db: Database) -> None:
    async with db.session() as session:
        job = await _make_job(session)
        resume = Resume(
            name="Base",
            file_type=ResumeFileType.docx,
            source_filename="cv.docx",
            file_path="/tmp/cv.docx",
        )
        session.add(resume)
        await session.flush()

        app_row = Application(
            job_id=job.id,
            resume_id=resume.id,
            status=ApplicationStatus.saved,
            tags=["remote", "priority"],
        )
        session.add(app_row)
        await session.flush()
        app_id = app_row.id

    # Fresh session: one level of relationships loads eagerly (selectin) without error.
    async with db.session() as session:
        loaded = await session.get(Application, app_id)
        assert loaded is not None
        assert loaded.job.company == "Acme"
        assert loaded.resume is not None
        assert loaded.resume.name == "Base"
        assert loaded.tags == ["remote", "priority"]

    # Reverse navigation: load the parent at top level so its collection is eager.
    async with db.session() as session:
        job = await session.get(Job, loaded.job_id)
        assert job is not None
        assert [a.id for a in job.applications] == [app_id]


async def test_cascade_delete_job_removes_children(db: Database) -> None:
    async with db.session() as session:
        job = await _make_job(session)
        session.add(Application(job_id=job.id, status=ApplicationStatus.interested))
        session.add(ATSScore(job_id=job.id, overall_score=82.5, keyword_score=90.0))
        await session.flush()
        job_id = job.id

    async with db.session() as session:
        job = await session.get(Job, job_id)
        assert job is not None
        await session.delete(job)

    async with db.session() as session:
        apps = (await session.exec(select(Application))).all()
        scores = (await session.exec(select(ATSScore))).all()
        assert apps == []
        assert scores == []


async def test_full_artifact_graph(db: Database) -> None:
    """Build job → tailored resume → cover letter → application → approval."""
    async with db.session() as session:
        job = await _make_job(session, dedup_hash="acme:staff")
        base = Resume(
            name="Base",
            file_type=ResumeFileType.pdf,
            source_filename="b.pdf",
            file_path="/tmp/b.pdf",
        )
        session.add(base)
        await session.flush()

        tailored = TailoredResume(
            job_id=job.id,
            base_resume_id=base.id,
            content="tailored",
            score_before=60.0,
            score_after=88.0,
            diff="@@ summary @@",
        )
        cover = CoverLetter(job_id=job.id, resume_id=base.id, style=CoverLetterStyle.startup)
        session.add(tailored)
        session.add(cover)
        await session.flush()

        application = Application(
            job_id=job.id,
            resume_id=base.id,
            tailored_resume_id=tailored.id,
            cover_letter_id=cover.id,
            status=ApplicationStatus.ready,
        )
        session.add(application)
        await session.flush()

        approval = ApprovalWorkflow(
            application_id=application.id,
            tailored_resume_id=tailored.id,
            cover_letter_id=cover.id,
            state=ApprovalState.review_required,
            resume_preview="tailored",
        )
        session.add(approval)
        await session.flush()
        app_id = application.id

    async with db.session() as session:
        loaded = await session.get(Application, app_id)
        assert loaded is not None
        assert loaded.tailored_resume is not None
        assert loaded.tailored_resume.score_after == 88.0
        assert loaded.cover_letter is not None
        assert loaded.cover_letter.style is CoverLetterStyle.startup
        assert loaded.approvals[0].state is ApprovalState.review_required


@pytest.mark.parametrize(
    "weighted",
    [
        # keyword 30, skills 25, exp 20, edu 10, semantic 15 — sanity-check storage.
        {
            "keyword_score": 90,
            "skills_score": 80,
            "experience_score": 70,
            "education_score": 100,
            "semantic_score": 60,
        },
    ],
)
async def test_ats_score_subscores_persist(db: Database, weighted: dict[str, float]) -> None:
    async with db.session() as session:
        job = await _make_job(session, dedup_hash="acme:ats")
        score = ATSScore(
            job_id=job.id,
            missing_keywords=["pytorch"],
            matched_keywords=["python", "fastapi"],
            strengths=["strong backend"],
            weaknesses=["no ml ops"],
            suggestions=["add pytorch project"],
            **weighted,
        )
        session.add(score)
        await session.flush()
        score_id = score.id

    async with db.session() as session:
        loaded = await session.get(ATSScore, score_id)
        assert loaded is not None
        assert loaded.matched_keywords == ["python", "fastapi"]
        assert loaded.missing_keywords == ["pytorch"]
        assert loaded.keyword_score == 90
