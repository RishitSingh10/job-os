"""Approvals router — human-in-the-loop review gate for applications."""

from __future__ import annotations

from typing import Annotated

from core.applications.approval import ApprovalService
from core.applications.service import ApplicationService
from core.database.models import ApprovalWorkflow
from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.api.schemas.approvals import ApprovalCreate, ApprovalRead, RejectRequest
from backend.api.schemas.common import Page

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def open_approval(payload: ApprovalCreate, session: SessionDep) -> ApprovalWorkflow:
    """Open a review for an application, snapshotting its current artifacts."""
    application = await ApplicationService(session).get_or_404(payload.application_id)
    return await ApprovalService(session).create_for_application(application)


@router.get("", response_model=Page[ApprovalRead])
async def list_approvals(
    session: SessionDep,
    application_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[ApprovalRead]:
    items, total = await ApprovalService(session).list_for(
        application_id=application_id, offset=offset, limit=limit
    )
    return Page[ApprovalRead](
        items=[ApprovalRead.model_validate(a) for a in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{approval_id}", response_model=ApprovalRead)
async def get_approval(approval_id: int, session: SessionDep) -> ApprovalWorkflow:
    return await ApprovalService(session).get_or_404(approval_id)


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
async def approve(approval_id: int, session: SessionDep) -> ApprovalWorkflow:
    service = ApprovalService(session)
    approval = await service.get_or_404(approval_id)
    return await service.approve(approval)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
async def reject(approval_id: int, payload: RejectRequest, session: SessionDep) -> ApprovalWorkflow:
    service = ApprovalService(session)
    approval = await service.get_or_404(approval_id)
    return await service.reject(approval, reason=payload.reason)


@router.post("/{approval_id}/apply", response_model=ApprovalRead)
async def apply(approval_id: int, session: SessionDep) -> ApprovalWorkflow:
    """Confirm submission of an approved application.

    Requires the approval to be ``approved``. Phase 9 (browser automation) drives
    the actual submission through this same gate; here it records the manual apply.
    """
    service = ApprovalService(session)
    approval = await service.get_or_404(approval_id)
    application = await ApplicationService(session).get_or_404(approval.application_id)
    await service.mark_applying(approval)
    return await service.mark_applied(approval, application)
