"""Cover letter API schemas."""

from __future__ import annotations

from datetime import datetime

from core.database.enums import CoverLetterStyle, DocumentFormat
from pydantic import BaseModel, ConfigDict, Field


class CoverLetterRequest(BaseModel):
    job_id: int
    resume_id: int
    style: CoverLetterStyle = CoverLetterStyle.concise
    exports: list[DocumentFormat] = Field(default_factory=list)


class CoverLetterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    resume_id: int | None
    style: CoverLetterStyle
    version: int
    content: str
    pdf_path: str | None
    docx_path: str | None
    markdown_path: str | None
    model_used: str | None
    created_at: datetime
