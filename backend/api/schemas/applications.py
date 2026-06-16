"""Application API schemas (Create / Update / Read / status transition)."""

from __future__ import annotations

from datetime import datetime

from core.database.enums import ApplicationStatus
from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.jobs import JobRead


class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: int | None = None
    tailored_resume_id: int | None = None
    cover_letter_id: int | None = None
    status: ApplicationStatus = ApplicationStatus.saved
    notes: str = ""
    tags: list[str] = Field(default_factory=list)


class ApplicationUpdate(BaseModel):
    resume_id: int | None = None
    tailored_resume_id: int | None = None
    cover_letter_id: int | None = None
    status: ApplicationStatus | None = None
    notes: str | None = None
    tags: list[str] | None = None
    applied_at: datetime | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    resume_id: int | None
    tailored_resume_id: int | None
    cover_letter_id: int | None
    status: ApplicationStatus
    notes: str
    tags: list[str]
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    job: JobRead | None = None


class StatusCount(BaseModel):
    status: ApplicationStatus
    count: int
