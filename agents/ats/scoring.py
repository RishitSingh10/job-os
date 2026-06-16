"""Weighted ATS scoring.

Combines five sub-scores into an overall 0–100 score using the spec weights:

    keyword 30% · skills 25% · experience 20% · education 10% · semantic 15%

Every sub-score is a pure function of the resume + job text (plus an optional
precomputed semantic similarity), so results are deterministic and testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agents.ats.skills import (
    content_tokens,
    detect_degree_level,
    extract_keywords,
    extract_required_years,
    extract_skills,
)

# Sub-score weights (must sum to 1.0).
WEIGHTS = {
    "keyword": 0.30,
    "skills": 0.25,
    "experience": 0.20,
    "education": 0.10,
    "semantic": 0.15,
}


@dataclass
class ScoreBreakdown:
    """Full result of scoring a resume against a job."""

    overall: float = 0.0
    keyword: float = 0.0
    skills: float = 0.0
    experience: float = 0.0
    education: float = 0.0
    semantic: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity; safe for zero vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _ratio_score(matched: int, total: int, *, empty_default: float = 100.0) -> float:
    """matched/total as a 0–100 score; an empty requirement scores the default."""
    if total == 0:
        return empty_default
    return round(100.0 * matched / total, 2)


def score_keywords(resume_text: str, job_text: str) -> tuple[float, list[str], list[str]]:
    job_keywords = extract_keywords(job_text)
    resume_tokens = set(content_tokens(resume_text)) | extract_skills(resume_text)
    matched = [k for k in job_keywords if k in resume_tokens or k in resume_text.lower()]
    missing = [k for k in job_keywords if k not in matched]
    return _ratio_score(len(matched), len(job_keywords)), matched, missing


def score_skills(resume_text: str, job_text: str) -> tuple[float, list[str], list[str]]:
    job_skills = extract_skills(job_text)
    resume_skills = extract_skills(resume_text)
    matched = sorted(job_skills & resume_skills)
    missing = sorted(job_skills - resume_skills)
    return _ratio_score(len(matched), len(job_skills)), matched, missing


def score_experience(resume_text: str, job_text: str) -> float:
    required = extract_required_years(job_text)
    if required is None or required == 0:
        return 100.0
    candidate = extract_required_years(resume_text) or 0
    # Also count explicit "N years" phrasing in the resume.
    return round(min(1.0, candidate / required) * 100.0, 2)


def score_education(resume_text: str, job_text: str) -> float:
    required = detect_degree_level(job_text)
    if required == 0:
        return 100.0
    have = detect_degree_level(resume_text)
    if have >= required:
        return 100.0
    if have == 0:  # no degree at all
        return 0.0
    if have == required - 1:  # one level short
        return 60.0
    return 30.0


def aggregate(
    *,
    keyword: float,
    skills: float,
    experience: float,
    education: float,
    semantic: float,
) -> float:
    overall = (
        WEIGHTS["keyword"] * keyword
        + WEIGHTS["skills"] * skills
        + WEIGHTS["experience"] * experience
        + WEIGHTS["education"] * education
        + WEIGHTS["semantic"] * semantic
    )
    return round(overall, 2)


def build_analysis(b: ScoreBreakdown) -> None:
    """Populate strengths / weaknesses / suggestions from the computed sub-scores.

    Deterministic, gap-driven guidance (LLM-enhanced narrative arrives in Phase 7).
    Mutates ``b`` in place.
    """
    if b.matched_skills:
        b.strengths.append(f"Matches key skills: {', '.join(b.matched_skills[:8])}.")
    if b.experience >= 90:
        b.strengths.append("Meets the experience requirement.")
    if b.education >= 100 and b.semantic >= 60:
        b.strengths.append("Education and overall profile align well with the role.")

    if b.skills < 60 and b.missing_skills:
        b.weaknesses.append(f"Missing important skills: {', '.join(b.missing_skills[:8])}.")
    if b.keyword < 60:
        b.weaknesses.append("Low keyword overlap with the job description.")
    if b.experience < 60:
        b.weaknesses.append("Falls short of the stated experience requirement.")
    if b.education < 60:
        b.weaknesses.append("Education level may not meet the requirement.")

    if b.missing_skills:
        b.suggestions.append(
            f"Where truthful, surface experience with: {', '.join(b.missing_skills[:6])}."
        )
    if b.missing_keywords:
        b.suggestions.append(f"Incorporate relevant keywords: {', '.join(b.missing_keywords[:8])}.")
    if b.semantic < 50:
        b.suggestions.append(
            "Reframe your summary and bullet points to mirror the role's language and focus."
        )
    if not b.suggestions:
        b.suggestions.append("Strong match — tighten wording and quantify impact where possible.")
