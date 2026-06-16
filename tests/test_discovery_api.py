"""Tests for the discovery router (/api/discovery)."""

from __future__ import annotations

from httpx import AsyncClient

POSTING = {
    "title": "Senior AI Engineer",
    "company": "Acme",
    "url": "https://jobs.acme.com/1",
    "description": "Python, LLMs, FastAPI.",
}


async def test_manual_discovery_creates_jobs(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/discovery/run",
        json={"source": "manual", "postings": [POSTING]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "manual"
    assert body["fetched"] == 1
    assert body["created"] == 1
    assert len(body["created_job_ids"]) == 1

    # The created job is now retrievable via the jobs API.
    listing = (await client.get("/api/jobs")).json()
    assert listing["total"] == 1


async def test_manual_discovery_dedupes_on_rerun(client: AsyncClient) -> None:
    await client.post("/api/discovery/run", json={"source": "manual", "postings": [POSTING]})
    again = await client.post(
        "/api/discovery/run", json={"source": "manual", "postings": [POSTING]}
    )
    body = again.json()
    assert body["created"] == 0
    assert body["duplicates"] == 1


async def test_manual_without_postings_is_422(client: AsyncClient) -> None:
    resp = await client.post("/api/discovery/run", json={"source": "manual"})
    assert resp.status_code == 422
    assert "postings" in resp.json()["detail"].lower()


async def test_browser_source_deferred_to_phase_9(client: AsyncClient) -> None:
    resp = await client.post("/api/discovery/run", json={"source": "linkedin", "query": "ai"})
    assert resp.status_code == 422
    assert "phase 9" in resp.json()["detail"].lower()
