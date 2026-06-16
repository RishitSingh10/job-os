"""Tests for the scoring router (/api/scoring)."""

from __future__ import annotations

from httpx import AsyncClient

JD = (
    "Senior AI Engineer needing 5+ years of Python, FastAPI, machine learning, "
    "PyTorch, AWS, Docker, Kubernetes. Bachelor degree required."
)
RESUME = (
    "Senior engineer, 6 years Python, FastAPI, machine learning, PyTorch, AWS, "
    "Docker, Kubernetes. BSc Computer Science."
)


async def _seed(client: AsyncClient) -> tuple[int, int]:
    job = (
        await client.post(
            "/api/jobs",
            json={
                "title": "Senior AI Engineer",
                "company": "Acme",
                "url": "https://acme.com/1",
                "description": JD,
            },
        )
    ).json()
    resume = (await client.post("/api/resumes", json={"name": "CV", "content": RESUME})).json()
    return job["id"], resume["id"]


async def test_score_endpoint_returns_breakdown(client: AsyncClient) -> None:
    job_id, resume_id = await _seed(client)
    resp = await client.post("/api/scoring/score", json={"job_id": job_id, "resume_id": resume_id})
    assert resp.status_code == 200

    body = resp.json()
    assert body["overall_score"] > 0
    for key in (
        "keyword_score",
        "skills_score",
        "experience_score",
        "education_score",
        "semantic_score",
    ):
        assert 0 <= body[key] <= 100
    assert body["matched_keywords"]
    assert isinstance(body["suggestions"], list)


async def test_scores_are_listed_and_fetchable(client: AsyncClient) -> None:
    job_id, resume_id = await _seed(client)
    created = (
        await client.post("/api/scoring/score", json={"job_id": job_id, "resume_id": resume_id})
    ).json()

    listing = (await client.get("/api/scoring/scores", params={"job_id": job_id})).json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == created["id"]

    one = await client.get(f"/api/scoring/scores/{created['id']}")
    assert one.status_code == 200


async def test_score_unknown_job_is_404(client: AsyncClient) -> None:
    _, resume_id = await _seed(client)
    resp = await client.post("/api/scoring/score", json={"job_id": 999999, "resume_id": resume_id})
    assert resp.status_code == 404
