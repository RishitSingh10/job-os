"""Manual adapter — ingest a caller-supplied list of postings.

Backs the "import these jobs" API path and is the seam the Phase 9 browser
scrapers feed into (they produce :class:`JobPosting` objects; this adapter / the
DiscoveryAgent handle dedup + indexing).
"""

from __future__ import annotations

from collections.abc import Iterable

from core.database.enums import JobSource

from agents.discovery.adapters.base import JobPosting


class ManualAdapter:
    """Returns a fixed set of postings (optionally filtered by a query substring)."""

    source: JobSource = JobSource.manual

    def __init__(self, postings: Iterable[JobPosting]) -> None:
        self._postings = list(postings)

    async def fetch(self, query: str, *, limit: int = 25) -> list[JobPosting]:
        postings = self._postings
        if query:
            needle = query.lower()
            postings = [
                p
                for p in postings
                if needle in p.title.lower()
                or needle in p.company.lower()
                or needle in p.description.lower()
            ]
        return postings[:limit]
