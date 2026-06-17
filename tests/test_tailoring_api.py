"""API tests for tailoring and cover letters (with a stubbed LLM)."""

from __future__ import annotations

import pytest
from backend.api.deps import get_llm
from core.llm import StubLLMClient
from fastapi import FastAPI
from httpx import AsyncClient

JD = "Senior Python Engineer with FastAPI and Docker. 5+ years."
RESUME = "Python and FastAPI engineer, 6 years building APIs."


@pytest.fixture(autouse=True)
def _stub_llm(app: FastAPI) -> None:
    """Inject a deterministic LLM for all tests in this module."""
    app.dependency_overrides[get_llm] = lambda: StubLLMClient(
        text="Summary: Python and FastAPI engineer with 6 years of API experience."
    )
    yield
    app.dependency_overrides.clear()


async def _seed(client: AsyncClient) -> tuple[int, int]:
    job = (
        await client.post(
            "/api/jobs",
            json={
                "title": "Senior Python Engineer",
                "company": "Acme",
                "url": "https://acme.com/1",
                "description": JD,
            },
        )
    ).json()
    resume = (await client.post("/api/resumes", json={"name": "CV", "content": RESUME})).json()
    return job["id"], resume["id"]


async def test_tailor_endpoint_returns_audit_and_scores(client: AsyncClient) -> None:
    job_id, resume_id = await _seed(client)
    resp = await client.post(
        "/api/tailoring/tailor", json={"base_resume_id": resume_id, "job_id": job_id}
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["resume"]["version"] == 1
    assert body["resume"]["content"].startswith("Summary:")
    assert "truthful" in body
    assert isinstance(body["introduced_skills"], list)
    assert "score_delta" in body


async def test_tailored_resumes_are_listed(client: AsyncClient) -> None:
    job_id, resume_id = await _seed(client)
    await client.post("/api/tailoring/tailor", json={"base_resume_id": resume_id, "job_id": job_id})
    listing = (await client.get("/api/tailoring/tailored", params={"job_id": job_id})).json()
    assert listing["total"] == 1


async def test_cover_letter_endpoint(client: AsyncClient) -> None:
    job_id, resume_id = await _seed(client)
    resp = await client.post(
        "/api/cover-letters",
        json={"job_id": job_id, "resume_id": resume_id, "style": "enterprise"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["style"] == "enterprise"
    assert body["content"]

    listing = (await client.get("/api/cover-letters", params={"job_id": job_id})).json()
    assert listing["total"] == 1
