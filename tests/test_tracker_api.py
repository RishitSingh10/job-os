"""API tests for the tracker board, tag filtering, and approval workflow."""

from __future__ import annotations

from httpx import AsyncClient

JOB = {"title": "ML Engineer", "company": "Acme", "url": "https://acme.com/9"}


async def _job(client: AsyncClient) -> int:
    return (await client.post("/api/jobs", json=JOB)).json()["id"]


async def test_board_groups_by_status(client: AsyncClient) -> None:
    job_id = await _job(client)
    a1 = (await client.post("/api/applications", json={"job_id": job_id})).json()["id"]
    await client.post("/api/applications", json={"job_id": job_id, "status": "interview"})
    await client.put(f"/api/applications/{a1}/status", json={"status": "applied"})

    board = (await client.get("/api/applications/board")).json()
    assert len(board) == 11  # one column per status
    by_status = {col["status"]: col for col in board}
    assert by_status["applied"]["count"] == 1
    assert by_status["interview"]["count"] == 1
    assert by_status["saved"]["count"] == 0
    assert by_status["applied"]["items"][0]["job"]["id"] == job_id


async def test_tag_filter(client: AsyncClient) -> None:
    job_id = await _job(client)
    await client.post("/api/applications", json={"job_id": job_id, "tags": ["remote", "dream"]})
    await client.post("/api/applications", json={"job_id": job_id, "tags": ["onsite"]})

    remote = (await client.get("/api/applications", params={"tag": "remote"})).json()
    assert remote["total"] == 1
    assert "remote" in remote["items"][0]["tags"]


async def test_approval_lifecycle(client: AsyncClient) -> None:
    job_id = await _job(client)
    app_id = (await client.post("/api/applications", json={"job_id": job_id})).json()["id"]

    opened = await client.post("/api/approvals", json={"application_id": app_id})
    assert opened.status_code == 201
    approval = opened.json()
    assert approval["state"] == "review_required"

    # Application moved to pending_approval.
    app = (await client.get(f"/api/applications/{app_id}")).json()
    assert app["status"] == "pending_approval"

    approved = await client.post(f"/api/approvals/{approval['id']}/approve")
    assert approved.json()["state"] == "approved"

    applied = await client.post(f"/api/approvals/{approval['id']}/apply")
    assert applied.json()["state"] == "applied"

    app = (await client.get(f"/api/applications/{app_id}")).json()
    assert app["status"] == "applied"
    assert app["applied_at"] is not None


async def test_apply_without_approval_conflicts(client: AsyncClient) -> None:
    job_id = await _job(client)
    app_id = (await client.post("/api/applications", json={"job_id": job_id})).json()["id"]
    approval = (await client.post("/api/approvals", json={"application_id": app_id})).json()

    resp = await client.post(f"/api/approvals/{approval['id']}/apply")
    assert resp.status_code == 409


async def test_reject_path(client: AsyncClient) -> None:
    job_id = await _job(client)
    app_id = (await client.post("/api/applications", json={"job_id": job_id})).json()["id"]
    approval = (await client.post("/api/approvals", json={"application_id": app_id})).json()

    rejected = await client.post(
        f"/api/approvals/{approval['id']}/reject", json={"reason": "low score"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"
    assert rejected.json()["reject_reason"] == "low score"
