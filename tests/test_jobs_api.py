"""Tests for the jobs router."""

from __future__ import annotations

from httpx import AsyncClient

JOB = {
    "title": "Senior AI Engineer",
    "company": "Acme",
    "url": "https://jobs.acme.com/123",
    "source": "linkedin",
    "easy_apply": True,
    "description": "Build LLM systems with Python and FastAPI.",
}


async def test_create_and_get_job(client: AsyncClient) -> None:
    resp = await client.post("/api/jobs", json=JOB)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["dedup_hash"]
    assert body["source"] == "linkedin"

    got = await client.get(f"/api/jobs/{body['id']}")
    assert got.status_code == 200
    assert got.json()["title"] == JOB["title"]


async def test_create_is_deduplicated(client: AsyncClient) -> None:
    first = (await client.post("/api/jobs", json=JOB)).json()
    second = (await client.post("/api/jobs", json=JOB)).json()
    assert first["id"] == second["id"]  # same fingerprint → same row

    listing = (await client.get("/api/jobs")).json()
    assert listing["total"] == 1


async def test_list_filters_and_pagination(client: AsyncClient) -> None:
    await client.post("/api/jobs", json=JOB)
    await client.post(
        "/api/jobs",
        json={
            **JOB,
            "title": "Data Scientist",
            "url": "https://x.io/1",
            "company": "Globex",
            "description": "Statistics, R, and experimentation.",
        },
    )

    all_jobs = (await client.get("/api/jobs")).json()
    assert all_jobs["total"] == 2
    assert all_jobs["limit"] == 50

    filtered = (await client.get("/api/jobs", params={"company": "globex"})).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["company"] == "Globex"

    searched = (await client.get("/api/jobs", params={"search": "FastAPI"})).json()
    assert searched["total"] == 1

    paged = (await client.get("/api/jobs", params={"limit": 1})).json()
    assert len(paged["items"]) == 1
    assert paged["total"] == 2


async def test_update_and_delete_job(client: AsyncClient) -> None:
    job = (await client.post("/api/jobs", json=JOB)).json()

    patched = await client.patch(f"/api/jobs/{job['id']}", json={"salary": "$200k"})
    assert patched.status_code == 200
    assert patched.json()["salary"] == "$200k"

    deleted = await client.delete(f"/api/jobs/{job['id']}")
    assert deleted.status_code == 200

    missing = await client.get(f"/api/jobs/{job['id']}")
    assert missing.status_code == 404
    assert "not found" in missing.json()["detail"].lower()


async def test_get_missing_job_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/api/jobs/999999")
    assert resp.status_code == 404
