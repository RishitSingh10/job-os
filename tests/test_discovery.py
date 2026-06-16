"""Unit tests for embeddings, the vector store, and the Discovery Agent."""

from __future__ import annotations

import math

import pytest_asyncio
from agents.discovery import DiscoveryAgent
from agents.discovery.adapters import JobPosting, ManualAdapter
from core.config import Settings
from core.database import Database
from core.database.enums import JobSource
from core.embeddings import DeterministicEmbedder, VectorStore
from core.jobs.service import JobService


def _posting(title: str, company: str, url: str, description: str = "Build things.") -> JobPosting:
    return JobPosting(
        title=title, company=company, url=url, description=description, source=JobSource.manual
    )


@pytest_asyncio.fixture
async def vector_store(settings: Settings) -> VectorStore:
    return VectorStore(settings, collection="test")


# ── Embedder ────────────────────────────────────────────────────────────────
async def test_deterministic_embedder_is_stable_and_unit_norm() -> None:
    emb = DeterministicEmbedder(dimensions=128)
    a = await emb.embed_one("Senior AI Engineer at Acme")
    b = await emb.embed_one("Senior AI Engineer at Acme")
    c = await emb.embed_one("Pastry chef in Paris")

    assert a == b  # deterministic
    assert a != c
    assert emb.dimensions == 128
    assert math.isclose(sum(x * x for x in a), 1.0, abs_tol=1e-9)


# ── VectorStore ───────────────────────────────────────────────────────────────
async def test_vector_store_upsert_query_delete(vector_store: VectorStore) -> None:
    emb = DeterministicEmbedder()
    v1 = await emb.embed_one("python fastapi backend engineer")
    v2 = await emb.embed_one("react frontend designer")

    await vector_store.upsert(
        ids=["1", "2"],
        embeddings=[v1, v2],
        documents=["a", "b"],
        metadatas=[{"job_id": 1}, {"job_id": 2}],
    )
    assert await vector_store.count() == 2

    hits = await vector_store.query(v1, n_results=1)
    assert hits[0].id == "1"
    assert hits[0].distance < 0.01  # identical vector → ~0 cosine distance

    await vector_store.delete(["1", "2"])
    assert await vector_store.count() == 0


# ── DiscoveryAgent ────────────────────────────────────────────────────────────
async def test_discovery_creates_and_indexes(db: Database, vector_store: VectorStore) -> None:
    async with db.session() as session:
        agent = DiscoveryAgent(session, embedder=DeterministicEmbedder(), vector_store=vector_store)
        adapter = ManualAdapter(
            [
                _posting("AI Engineer", "Acme", "https://acme.com/1"),
                _posting("Data Scientist", "Globex", "https://globex.com/2"),
            ]
        )
        result = await agent.discover(adapter, query="")

    assert result.fetched == 2
    assert result.created == 2
    assert result.indexed == 2
    assert result.duplicates == 0
    assert result.semantic_enabled is True
    assert len(result.created_job_ids) == 2
    assert await vector_store.count() == 2

    # embedding_id was persisted on the created jobs
    async with db.session() as session:
        job = await JobService(session).get(result.created_job_ids[0])
        assert job is not None and job.embedding_id is not None


async def test_discovery_dedupes_exact_and_tracking_url(
    db: Database, vector_store: VectorStore
) -> None:
    async with db.session() as session:
        agent = DiscoveryAgent(session, embedder=DeterministicEmbedder(), vector_store=vector_store)
        first = await agent.discover(
            ManualAdapter([_posting("AI Engineer", "Acme", "https://acme.com/jobs/1")]),
            query="",
        )
        assert first.created == 1

        # Same posting (identical) + same posting with only a tracking query param.
        second = await agent.discover(
            ManualAdapter(
                [
                    _posting("AI Engineer", "Acme", "https://acme.com/jobs/1"),
                    _posting("AI Engineer", "Acme", "https://acme.com/jobs/1?utm=linkedin"),
                ]
            ),
            query="",
        )
    assert second.created == 0
    assert second.duplicates == 2


async def test_discovery_fuzzy_title_dedupe(db: Database, vector_store: VectorStore) -> None:
    async with db.session() as session:
        agent = DiscoveryAgent(session, embedder=DeterministicEmbedder(), vector_store=vector_store)
        await agent.discover(
            ManualAdapter([_posting("Senior ML Engineer", "Acme", "https://a.co/1")]), query=""
        )
        # Near-identical title, same company, different URL → fuzzy duplicate.
        result = await agent.discover(
            ManualAdapter([_posting("Senior  ML  Engineer!", "Acme", "https://a.co/2")]),
            query="",
        )
    assert result.created == 0
    assert result.duplicates == 1


async def test_discovery_without_embeddings_still_dedupes(db: Database) -> None:
    """No embedder/store → fingerprint + fuzzy dedup still works."""
    async with db.session() as session:
        agent = DiscoveryAgent(session, embedder=None, vector_store=None)
        adapter = ManualAdapter([_posting("AI Engineer", "Acme", "https://acme.com/1")])
        first = await agent.discover(adapter, query="")
        second = await agent.discover(adapter, query="")

    assert first.created == 1
    assert first.indexed == 0
    assert first.semantic_enabled is False
    assert second.duplicates == 1


async def test_dry_run_creates_nothing(db: Database, vector_store: VectorStore) -> None:
    async with db.session() as session:
        agent = DiscoveryAgent(session, embedder=DeterministicEmbedder(), vector_store=vector_store)
        result = await agent.discover(
            ManualAdapter([_posting("AI Engineer", "Acme", "https://acme.com/1")]),
            query="",
            dry_run=True,
        )
        assert result.created == 1  # would-create count
        assert result.created_job_ids == []
        assert (await JobService(session).count()) == 0
