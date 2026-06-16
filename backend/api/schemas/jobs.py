"""Job API schemas (Create / Update / Read)."""

from __future__ import annotations

from datetime import datetime

from core.database.enums import JobSource
from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    title: str
    company: str
    location: str | None = None
    salary: str | None = None
    url: str
    easy_apply: bool = False
    description: str = ""
    source: JobSource = JobSource.manual
    external_id: str | None = None
    posted_at: datetime | None = None


class JobCreate(JobBase):
    """Payload to create a job. ``dedup_hash`` is derived server-side."""


class JobUpdate(BaseModel):
    """Partial update — every field optional."""

    title: str | None = None
    company: str | None = None
    location: str | None = None
    salary: str | None = None
    url: str | None = None
    easy_apply: bool | None = None
    description: str | None = None
    source: JobSource | None = None
    external_id: str | None = None
    posted_at: datetime | None = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dedup_hash: str
    embedding_id: str | None
    created_at: datetime
    updated_at: datetime
