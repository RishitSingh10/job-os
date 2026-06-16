"""Tests for the applications router."""

from __future__ import annotations

from httpx import AsyncClient

JOB = {"title": "ML Engineer", "company": "Acme", "url": "https://jobs.acme.com/9"}


async def _make_job(client: AsyncClient) -> int:
    return (await client.post("/api/jobs", json=JOB)).json()["id"]


async def test_create_application_embeds_job(client: AsyncClient) -> None:
    job_id = await _make_job(client)
    resp = await client.post("/api/applications", json={"job_id": job_id, "tags": ["remote"]})
    assert resp.status_code == 201

    body = resp.json()
    assert body["status"] == "saved"
    assert body["tags"] == ["remote"]
    assert body["job"]["id"] == job_id  # nested job eagerly loaded
    assert body["applied_at"] is None


async def test_create_application_with_unknown_job_404(client: AsyncClient) -> None:
    resp = await client.post("/api/applications", json={"job_id": 424242})
    assert resp.status_code == 404


async def test_status_transition_stamps_applied_at(client: AsyncClient) -> None:
    job_id = await _make_job(client)
    app_id = (await client.post("/api/applications", json={"job_id": job_id})).json()["id"]

    resp = await client.put(f"/api/applications/{app_id}/status", json={"status": "applied"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "applied"
    assert body["applied_at"] is not None


async def test_list_and_filter_by_status(client: AsyncClient) -> None:
    job_id = await _make_job(client)
    a1 = (await client.post("/api/applications", json={"job_id": job_id})).json()["id"]
    await client.post("/api/applications", json={"job_id": job_id, "status": "interested"})

    await client.put(f"/api/applications/{a1}/status", json={"status": "applied"})

    applied = (await client.get("/api/applications", params={"status": "applied"})).json()
    assert applied["total"] == 1
    assert applied["items"][0]["id"] == a1

    everything = (await client.get("/api/applications")).json()
    assert everything["total"] == 2


async def test_counts_by_status(client: AsyncClient) -> None:
    job_id = await _make_job(client)
    await client.post("/api/applications", json={"job_id": job_id})
    await client.post("/api/applications", json={"job_id": job_id, "status": "interested"})

    counts = (await client.get("/api/applications/counts")).json()
    by_status = {row["status"]: row["count"] for row in counts}
    assert by_status["saved"] == 1
    assert by_status["interested"] == 1
    assert by_status["offer"] == 0
    # Every status in the enum is represented.
    assert len(counts) == 11
