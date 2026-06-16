"""Discovery API schemas."""

from __future__ import annotations

from datetime import datetime

from core.database.enums import JobSource
from pydantic import BaseModel, Field


class PostingInput(BaseModel):
    """A posting supplied by the client for manual import / discovery."""

    title: str
    company: str
    url: str
    location: str | None = None
    salary: str | None = None
    description: str = ""
    easy_apply: bool = False
    external_id: str | None = None
    posted_at: datetime | None = None


class DiscoveryRunRequest(BaseModel):
    source: JobSource
    query: str = ""
    limit: int = Field(default=25, ge=1, le=100)
    dry_run: bool = False
    # Required when source == manual; ignored otherwise.
    postings: list[PostingInput] | None = None


class DiscoveryRunResponse(BaseModel):
    source: str
    query: str
    fetched: int
    created: int
    duplicates: int
    indexed: int
    semantic_enabled: bool
    created_job_ids: list[int]
