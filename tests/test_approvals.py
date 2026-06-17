"""Unit tests for the approval workflow state machine."""

from __future__ import annotations

import pytest
from core.applications.approval import ApprovalService
from core.applications.service import ApplicationService
from core.database import Database
from core.database.enums import ApplicationStatus, ApprovalState, JobSource, ResumeFileType
from core.database.models import Application, Job, Resume
from core.exceptions import ConflictError


async def _seed(session) -> int:
    job = Job(
        title="Engineer",
        company="Acme",
        url="https://acme.com/1",
        source=JobSource.manual,
        dedup_hash="acme:e",
        description="role",
    )
    resume = Resume(
        name="CV",
        file_type=ResumeFileType.pdf,
        source_filename="cv.pdf",
        file_path="/tmp/cv.pdf",
        content="Python engineer.",
    )
    session.add(job)
    session.add(resume)
    await session.flush()
    app = Application(job_id=job.id, resume_id=resume.id, status=ApplicationStatus.ready)
    session.add(app)
    await session.flush()
    return app.id


async def test_open_sets_review_required_and_pending(db: Database) -> None:
    async with db.session() as session:
        app_id = await _seed(session)
        application = await ApplicationService(session).get_or_404(app_id)
        approval = await ApprovalService(session).create_for_application(application)

        assert approval.state is ApprovalState.review_required
        assert approval.resume_preview is not None  # snapshotted from the resume
        assert application.status is ApplicationStatus.pending_approval


async def test_approve_then_apply_marks_application_applied(db: Database) -> None:
    async with db.session() as session:
        app_id = await _seed(session)
        appsvc = ApplicationService(session)
        application = await appsvc.get_or_404(app_id)
        svc = ApprovalService(session)

        approval = await svc.create_for_application(application)
        await svc.approve(approval)
        assert approval.state is ApprovalState.approved
        assert approval.decided_at is not None

        await svc.mark_applying(approval)
        await svc.mark_applied(approval, application)
        assert approval.state is ApprovalState.applied
        assert application.status is ApplicationStatus.applied
        assert application.applied_at is not None


async def test_cannot_apply_without_approval(db: Database) -> None:
    async with db.session() as session:
        app_id = await _seed(session)
        application = await ApplicationService(session).get_or_404(app_id)
        svc = ApprovalService(session)
        approval = await svc.create_for_application(application)

        with pytest.raises(ConflictError):
            await svc.mark_applying(approval)  # review_required → applying is illegal


async def test_reject_records_reason(db: Database) -> None:
    async with db.session() as session:
        app_id = await _seed(session)
        application = await ApplicationService(session).get_or_404(app_id)
        svc = ApprovalService(session)
        approval = await svc.create_for_application(application)

        await svc.reject(approval, reason="ATS score too low")
        assert approval.state is ApprovalState.rejected
        assert approval.reject_reason == "ATS score too low"

        with pytest.raises(ConflictError):
            await svc.approve(approval)  # terminal state
