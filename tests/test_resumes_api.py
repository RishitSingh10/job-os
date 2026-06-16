"""Tests for the resumes router."""

from __future__ import annotations

from httpx import AsyncClient


async def test_resume_crud_lifecycle(client: AsyncClient) -> None:
    create = await client.post(
        "/api/resumes",
        json={
            "name": "Backend CV",
            "file_type": "pdf",
            "content": "Python, FastAPI, SQL",
            "sections": [{"heading": "Skills", "text": "Python"}],
        },
    )
    assert create.status_code == 201
    resume = create.json()
    assert resume["is_base"] is True
    assert resume["sections"] == [{"heading": "Skills", "text": "Python"}]

    patched = await client.patch(f"/api/resumes/{resume['id']}", json={"name": "Backend CV v2"})
    assert patched.status_code == 200
    assert patched.json()["name"] == "Backend CV v2"

    deleted = await client.delete(f"/api/resumes/{resume['id']}")
    assert deleted.status_code == 200
    assert (await client.get(f"/api/resumes/{resume['id']}")).status_code == 404


async def test_resume_filtering(client: AsyncClient) -> None:
    await client.post("/api/resumes", json={"name": "Base CV", "is_base": True})
    await client.post("/api/resumes", json={"name": "Variant", "is_base": False})

    base_only = (await client.get("/api/resumes", params={"is_base": True})).json()
    assert base_only["total"] == 1
    assert base_only["items"][0]["name"] == "Base CV"

    searched = (await client.get("/api/resumes", params={"search": "variant"})).json()
    assert searched["total"] == 1
