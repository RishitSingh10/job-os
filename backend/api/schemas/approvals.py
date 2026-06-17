"""Approval workflow API schemas."""

from __future__ import annotations

from datetime import datetime

from core.database.enums import ApprovalState
from pydantic import BaseModel, ConfigDict


class ApprovalCreate(BaseModel):
    application_id: int


class RejectRequest(BaseModel):
    reason: str | None = None


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    ats_score_id: int | None
    tailored_resume_id: int | None
    cover_letter_id: int | None
    state: ApprovalState
    resume_preview: str | None
    cover_letter_preview: str | None
    diff_preview: str | None
    reject_reason: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
