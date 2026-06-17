"""Resume tailoring API schemas."""

from __future__ import annotations

from datetime import datetime

from core.database.enums import DocumentFormat
from pydantic import BaseModel, ConfigDict, Field


class TailorRequest(BaseModel):
    base_resume_id: int
    job_id: int
    exports: list[DocumentFormat] = Field(default_factory=list)


class TailoredResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    base_resume_id: int
    version: int
    content: str
    diff: str | None
    score_before: float | None
    score_after: float | None
    pdf_path: str | None
    docx_path: str | None
    markdown_path: str | None
    html_path: str | None
    model_used: str | None
    created_at: datetime


class TailorResult(BaseModel):
    """Tailoring response: the stored resume plus the truthfulness audit."""

    resume: TailoredResumeRead
    truthful: bool
    introduced_skills: list[str]
    score_delta: float
