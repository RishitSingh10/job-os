"""Unit tests for ATS scoring logic and the ATS agent."""

from __future__ import annotations

import math

from agents.ats.agent import ATSAgent
from agents.ats.scoring import (
    WEIGHTS,
    score_education,
    score_experience,
    score_skills,
)
from agents.ats.skills import detect_degree_level, extract_required_years, extract_skills
from core.database import Database
from core.database.enums import JobSource, ResumeFileType
from core.database.models import Job, Resume
from core.embeddings import DeterministicEmbedder

JD = (
    "Senior AI Engineer. We need 5+ years building Python and FastAPI backends with "
    "machine learning, PyTorch, AWS, Docker, and Kubernetes. Bachelor degree required."
)
MATCHING_RESUME = (
    "Senior engineer with 6 years of Python and FastAPI, machine learning, PyTorch, "
    "AWS, Docker, and Kubernetes. BSc in Computer Science."
)
MISMATCH_RESUME = "Pastry chef baking bread and cakes in a Paris bakery."


def test_weights_sum_to_one() -> None:
    assert math.isclose(sum(WEIGHTS.values()), 1.0)


def test_skill_extraction_and_match() -> None:
    assert {"python", "fastapi", "pytorch", "aws", "docker", "kubernetes"} <= extract_skills(JD)
    score, matched, missing = score_skills(MATCHING_RESUME, JD)
    assert "machine learning" in matched
    assert score >= 90
    assert missing == [] or score >= 90


def test_experience_scoring() -> None:
    assert extract_required_years(JD) == 5
    assert score_experience(MATCHING_RESUME, JD) == 100.0  # 6 >= 5
    assert score_experience("2 years of Python", JD) == 40.0  # 2/5
    assert score_experience("No numbers here", JD) == 0.0
    assert score_experience("anything", "no requirement stated") == 100.0


def test_education_scoring() -> None:
    assert detect_degree_level(JD) == 1  # bachelor
    assert score_education(MATCHING_RESUME, JD) == 100.0  # BSc >= bachelor
    assert score_education("PhD in ML", JD) == 100.0
    assert score_education("No degree mentioned", JD) == 0.0


async def test_agent_evaluate_ranks_match_above_mismatch(db: Database) -> None:
    async with db.session() as session:
        agent = ATSAgent(session, embedder=DeterministicEmbedder())
        good = await agent.evaluate(MATCHING_RESUME, JD)
        bad = await agent.evaluate(MISMATCH_RESUME, JD)

    assert good.overall > bad.overall
    assert good.overall >= 65
    assert bad.overall <= 45
    assert 0 <= good.semantic <= 100
    assert good.suggestions  # always offers guidance
    assert any("skill" in w.lower() for w in bad.weaknesses)


async def test_agent_score_persists(db: Database) -> None:
    async with db.session() as session:
        job = Job(
            title="Senior AI Engineer",
            company="Acme",
            url="https://acme.com/1",
            source=JobSource.manual,
            dedup_hash="acme:ai",
            description=JD,
        )
        resume = Resume(
            name="CV",
            file_type=ResumeFileType.pdf,
            source_filename="cv.pdf",
            file_path="/tmp/cv.pdf",
            content=MATCHING_RESUME,
        )
        session.add(job)
        session.add(resume)
        await session.flush()

        agent = ATSAgent(session, embedder=DeterministicEmbedder())
        score = await agent.score(job_id=job.id, resume_id=resume.id)

        assert score.id is not None
        assert score.overall_score >= 65
        assert score.model_used == "deterministic+embeddings"
        assert score.matched_keywords

        latest = await agent.scores.latest_for(job_id=job.id, resume_id=resume.id)
        assert latest is not None and latest.id == score.id
