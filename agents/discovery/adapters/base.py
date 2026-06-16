"""Adapter contract and the normalised posting DTO."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from core.database.enums import JobSource
from core.database.models import Job
from core.jobs.dedup import make_dedup_hash
from pydantic import BaseModel


class JobPosting(BaseModel):
    """A source-agnostic job posting, before it becomes a persisted :class:`Job`."""

    title: str
    company: str
    url: str
    location: str | None = None
    salary: str | None = None
    description: str = ""
    easy_apply: bool = False
    source: JobSource
    external_id: str | None = None
    posted_at: datetime | None = None

    def embedding_text(self) -> str:
        """The text used for embedding/semantic dedup."""
        parts = [self.title, self.company, self.location or "", self.description]
        return "\n".join(p for p in parts if p).strip()

    def to_job(self) -> Job:
        """Materialise a persistable :class:`Job` with its dedup fingerprint."""
        return Job(
            title=self.title,
            company=self.company,
            location=self.location,
            salary=self.salary,
            url=self.url,
            easy_apply=self.easy_apply,
            description=self.description,
            source=self.source,
            external_id=self.external_id,
            posted_at=self.posted_at,
            dedup_hash=make_dedup_hash(title=self.title, company=self.company, url=self.url),
        )


@runtime_checkable
class JobSourceAdapter(Protocol):
    """Fetches and normalises postings from a single source."""

    source: JobSource

    async def fetch(self, query: str, *, limit: int = 25) -> list[JobPosting]: ...
