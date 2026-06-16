"""Job service — CRUD plus discovery-oriented queries and dedup-aware creation."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import or_, select

from core.database.crud import CRUDService
from core.database.enums import JobSource
from core.database.models import Job
from core.jobs.dedup import make_dedup_hash


class JobService(CRUDService[Job]):
    model = Job

    async def get_by_dedup_hash(self, dedup_hash: str) -> Job | None:
        stmt = select(Job).where(Job.dedup_hash == dedup_hash)
        return (await self.session.exec(stmt)).first()

    async def upsert(self, job: Job) -> tuple[Job, bool]:
        """Create the job, or return the existing one if its fingerprint matches.

        Returns ``(job, created)``. The dedup hash is computed here if missing so
        callers never have to. This is the deterministic first-pass dedup; richer
        similarity matching arrives in Phase 5.
        """
        if not job.dedup_hash:
            job.dedup_hash = make_dedup_hash(title=job.title, company=job.company, url=job.url)
        existing = await self.get_by_dedup_hash(job.dedup_hash)
        if existing is not None:
            return existing, False
        return await self.create(job), True

    async def list_jobs(
        self,
        *,
        source: JobSource | None = None,
        company: str | None = None,
        easy_apply: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Job], int]:
        conditions = []
        if source is not None:
            conditions.append(Job.source == source)
        if company:
            conditions.append(Job.company.ilike(f"%{company}%"))  # type: ignore[attr-defined]
        if easy_apply is not None:
            conditions.append(Job.easy_apply == easy_apply)
        if search:
            like = f"%{search}%"
            conditions.append(
                or_(
                    Job.title.ilike(like),  # type: ignore[attr-defined]
                    Job.company.ilike(like),  # type: ignore[attr-defined]
                    Job.description.ilike(like),  # type: ignore[attr-defined]
                )
            )
        return await self.list(conditions=conditions, offset=offset, limit=limit)
