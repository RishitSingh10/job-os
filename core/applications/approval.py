"""Human-in-the-loop approval workflow.

An :class:`~core.database.models.ApprovalWorkflow` is the gate that stands between a
prepared application and an automated submission. The state machine is::

    review_required ──approve──▶ approved ──apply──▶ applying ──▶ applied
            │                        │                   │
            └────────reject──────────┴───────────────────┴──▶ rejected

Nothing transitions to ``applying``/``applied`` without first passing through
``approved`` — enforcing the spec rule that applications are never auto-submitted
without explicit human approval.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import select

from core.database.base import utcnow
from core.database.crud import CRUDService
from core.database.enums import ApplicationStatus, ApprovalState
from core.database.models import (
    ApprovalWorkflow,
    ATSScore,
    CoverLetter,
    TailoredResume,
)
from core.exceptions import ConflictError
from core.logging import get_logger

log = get_logger(__name__)

_PREVIEW_CHARS = 4000

# Allowed state transitions.
_TRANSITIONS: dict[ApprovalState, set[ApprovalState]] = {
    ApprovalState.generated: {
        ApprovalState.review_required,
        ApprovalState.approved,
        ApprovalState.rejected,
    },
    ApprovalState.review_required: {ApprovalState.approved, ApprovalState.rejected},
    ApprovalState.approved: {ApprovalState.applying, ApprovalState.rejected},
    ApprovalState.applying: {ApprovalState.applied, ApprovalState.rejected},
    ApprovalState.applied: set(),
    ApprovalState.rejected: set(),
}


def _preview(text: str | None) -> str | None:
    if not text:
        return None
    return text[:_PREVIEW_CHARS]


class ApprovalService(CRUDService[ApprovalWorkflow]):
    model = ApprovalWorkflow

    def _transition(self, approval: ApprovalWorkflow, target: ApprovalState) -> None:
        if target not in _TRANSITIONS[approval.state]:
            raise ConflictError(
                f"Cannot move approval from {approval.state.value} to {target.value}."
            )
        approval.state = target

    async def _latest_tailored(self, application) -> TailoredResume | None:
        if application.tailored_resume_id is not None:
            return await self.session.get(TailoredResume, application.tailored_resume_id)
        stmt = (
            select(TailoredResume)
            .where(TailoredResume.job_id == application.job_id)
            .order_by(TailoredResume.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        return (await self.session.exec(stmt)).first()

    async def _latest_cover_letter(self, application) -> CoverLetter | None:
        if application.cover_letter_id is not None:
            return await self.session.get(CoverLetter, application.cover_letter_id)
        stmt = (
            select(CoverLetter)
            .where(CoverLetter.job_id == application.job_id)
            .order_by(CoverLetter.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        return (await self.session.exec(stmt)).first()

    async def _latest_score(self, application) -> ATSScore | None:
        stmt = (
            select(ATSScore)
            .where(ATSScore.job_id == application.job_id)
            .order_by(ATSScore.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        return (await self.session.exec(stmt)).first()

    async def create_for_application(self, application) -> ApprovalWorkflow:
        """Open a review for an application, snapshotting its current artifacts."""
        tailored = await self._latest_tailored(application)
        cover = await self._latest_cover_letter(application)
        score = await self._latest_score(application)

        resume_preview = _preview(tailored.content if tailored else None)
        if resume_preview is None and application.resume is not None:
            resume_preview = _preview(application.resume.content)

        approval = await self.create(
            ApprovalWorkflow(
                application_id=application.id,
                ats_score_id=score.id if score else None,
                tailored_resume_id=tailored.id if tailored else None,
                cover_letter_id=cover.id if cover else None,
                state=ApprovalState.review_required,
                resume_preview=resume_preview,
                cover_letter_preview=_preview(cover.content if cover else None),
                diff_preview=_preview(tailored.diff if tailored else None),
            )
        )
        application.status = ApplicationStatus.pending_approval
        self.session.add(application)
        await self.session.flush()
        log.info("approval_opened", approval_id=approval.id, application_id=application.id)
        return approval

    async def approve(self, approval: ApprovalWorkflow) -> ApprovalWorkflow:
        self._transition(approval, ApprovalState.approved)
        approval.decided_at = utcnow()
        await self.update(approval, {})
        log.info("approval_approved", approval_id=approval.id)
        return approval

    async def reject(
        self, approval: ApprovalWorkflow, *, reason: str | None = None
    ) -> ApprovalWorkflow:
        self._transition(approval, ApprovalState.rejected)
        approval.reject_reason = reason
        approval.decided_at = utcnow()
        await self.update(approval, {})
        log.info("approval_rejected", approval_id=approval.id)
        return approval

    async def mark_applying(self, approval: ApprovalWorkflow) -> ApprovalWorkflow:
        self._transition(approval, ApprovalState.applying)
        return await self.update(approval, {})

    async def mark_applied(self, approval: ApprovalWorkflow, application) -> ApprovalWorkflow:
        self._transition(approval, ApprovalState.applied)
        application.status = ApplicationStatus.applied
        if application.applied_at is None:
            application.applied_at = utcnow()
        self.session.add(application)
        await self.update(approval, {})
        log.info("approval_applied", approval_id=approval.id, application_id=application.id)
        return approval

    async def list_for(
        self, *, application_id: int | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[Sequence[ApprovalWorkflow], int]:
        conditions = (
            [ApprovalWorkflow.application_id == application_id]
            if application_id is not None
            else []
        )
        return await self.list(conditions=conditions, offset=offset, limit=limit)
