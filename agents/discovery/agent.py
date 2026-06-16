"""Discovery Agent — fetch, deduplicate, persist, and index job postings.

Orchestrates a discovery run end to end:

1. Fetch normalised :class:`JobPosting` objects from a source adapter.
2. Deduplicate, cheapest signal first:
   a. exact fingerprint (``dedup_hash``),
   b. semantic similarity (embedding cosine distance) when embeddings are available,
   c. fuzzy title match against same-company jobs.
3. Persist new jobs and index their embeddings in the vector store.

Embeddings are best-effort: if Ollama is unreachable or ChromaDB isn't installed,
the run still completes using fingerprint + fuzzy dedup (semantic steps are skipped
and reported).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.database.models import Job
from core.embeddings import Embedder, VectorStore
from core.jobs.dedup import EMBEDDING_DISTANCE_THRESHOLD, is_title_duplicate
from core.jobs.service import JobService
from core.logging import get_logger

from agents.discovery.adapters.base import JobPosting, JobSourceAdapter

log = get_logger(__name__)


@dataclass
class DiscoveryResult:
    """Summary of a discovery run."""

    source: str
    query: str
    fetched: int = 0
    created: int = 0
    duplicates: int = 0
    indexed: int = 0
    semantic_enabled: bool = False
    created_job_ids: list[int] = field(default_factory=list)


class DiscoveryAgent:
    """Runs discovery for a single source adapter against the database."""

    def __init__(
        self,
        session,
        *,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.jobs = JobService(session)
        self._embedder = embedder
        self._vector_store = vector_store
        # Semantic dedup/indexing needs both an embedder and a store; it can also be
        # disabled mid-run if the embedder errors (e.g. Ollama down).
        self._semantic = embedder is not None and vector_store is not None

    async def discover(
        self, adapter: JobSourceAdapter, query: str, *, limit: int = 25, dry_run: bool = False
    ) -> DiscoveryResult:
        postings = await adapter.fetch(query, limit=limit)
        result = DiscoveryResult(source=str(adapter.source), query=query, fetched=len(postings))

        for posting in postings:
            embedding = await self._embed(posting)
            if await self._is_duplicate(posting, embedding):
                result.duplicates += 1
                continue

            if dry_run:
                result.created += 1
                continue

            job = await self.jobs.create(posting.to_job())
            result.created += 1
            result.created_job_ids.append(job.id)  # type: ignore[arg-type]

            if embedding is not None and await self._index(job, posting, embedding):
                result.indexed += 1

        result.semantic_enabled = self._semantic
        log.info(
            "discovery_run",
            source=result.source,
            fetched=result.fetched,
            created=result.created,
            duplicates=result.duplicates,
            indexed=result.indexed,
            semantic=result.semantic_enabled,
        )
        return result

    async def _embed(self, posting: JobPosting) -> list[float] | None:
        if not self._semantic or self._embedder is None:
            return None
        try:
            return await self._embedder.embed_one(posting.embedding_text())
        except Exception as exc:  # Ollama unreachable / model missing → degrade
            log.warning("embedding_failed", error=str(exc))
            self._semantic = False  # stop trying for the rest of this run
            return None

    async def _is_duplicate(self, posting: JobPosting, embedding: list[float] | None) -> bool:
        job = posting.to_job()

        # 1. Exact fingerprint.
        if await self.jobs.get_by_dedup_hash(job.dedup_hash) is not None:
            return True

        # 2. Semantic similarity.
        if embedding is not None and self._vector_store is not None:
            hits = await self._vector_store.query(embedding, n_results=1)
            if hits and hits[0].distance <= EMBEDDING_DISTANCE_THRESHOLD:
                return True

        # 3. Fuzzy title match within the same company.
        for candidate in await self.jobs.find_candidates_by_company(posting.company):
            if is_title_duplicate(posting.title, candidate.title):
                return True

        return False

    async def _index(self, job: Job, posting: JobPosting, embedding: list[float]) -> bool:
        if self._vector_store is None:
            return False
        job_id = str(job.id)
        await self._vector_store.upsert(
            ids=[job_id],
            embeddings=[embedding],
            documents=[posting.embedding_text()],
            metadatas=[{"job_id": job.id, "company": job.company, "title": job.title}],
        )
        await self.jobs.update(job, {"embedding_id": job_id})
        return True
