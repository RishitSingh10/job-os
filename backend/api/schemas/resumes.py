"""Resume API schemas (Create / Update / Read).

File upload + parsing arrives in Phase 7; for now resumes can be created with
already-extracted content/metadata.
"""

from __future__ import annotations

from datetime import datetime

from core.database.enums import ResumeFileType
from pydantic import BaseModel, ConfigDict, Field


class ResumeCreate(BaseModel):
    name: str
    file_type: ResumeFileType = ResumeFileType.pdf
    source_filename: str = ""
    file_path: str = ""
    content: str = ""
    sections: list[dict] = Field(default_factory=list)
    is_base: bool = True


class ResumeUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    sections: list[dict] | None = None
    is_base: bool | None = None


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    file_type: ResumeFileType
    source_filename: str
    file_path: str
    content: str
    sections: list[dict]
    embedding_id: str | None
    is_base: bool
    created_at: datetime
    updated_at: datetime
