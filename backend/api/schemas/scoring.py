"""ATS scoring API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScoreRequest(BaseModel):
    job_id: int
    resume_id: int


class ATSScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    resume_id: int | None
    tailored_resume_id: int | None
    overall_score: float
    keyword_score: float
    skills_score: float
    experience_score: float
    education_score: float
    semantic_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    model_used: str | None
    created_at: datetime
