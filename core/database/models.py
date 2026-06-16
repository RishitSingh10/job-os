"""SQLModel domain models for Job OS.

All persistent entities live here because they are tightly cross-referenced via
relationships; co-locating them keeps the mapper configuration unambiguous and
avoids import-ordering pitfalls. Supporting concerns are split out:
:mod:`core.database.enums` (enumerations) and :mod:`core.database.base`
(timestamp mixin, JSON column helper).

Relationship loading strategy: collections and scalar references use
``lazy="selectin"`` so they can be safely traversed under the async engine
without tripping the lazy-load greenlet error. Ownership edges
(job → its artifacts, application → its approvals/runs) cascade deletes at the
ORM layer.

Truthfulness note (enforced by the agents, recorded here): a
:class:`TailoredResume` is always derived from a real :class:`Resume`; nothing in
the schema fabricates experience.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship

from core.database.base import TimestampMixin, json_column
from core.database.enums import (
    ApplicationStatus,
    ApprovalState,
    AutomationPlatform,
    AutomationStatus,
    CoverLetterStyle,
    JobSource,
    ResumeFileType,
)

# Relationship loading presets.
_SEL: dict[str, str] = {"lazy": "selectin"}
_SEL_CASCADE: dict[str, str] = {"lazy": "selectin", "cascade": "all, delete-orphan"}


# ──────────────────────────────────────────────────────────────────────────
# Resume library
# ──────────────────────────────────────────────────────────────────────────
class Resume(TimestampMixin, table=True):
    """A base resume uploaded by the user (PDF/DOCX), parsed into text + sections."""

    __tablename__ = "resumes"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    file_type: ResumeFileType
    source_filename: str
    file_path: str  # absolute path under storage/base_resumes
    content: str = ""  # full extracted plain text
    sections: list[dict] = json_column()  # [{"heading": str, "text": str}, ...]
    embedding_id: str | None = Field(default=None, index=True)  # ChromaDB id
    is_base: bool = Field(default=True, index=True)

    tailored_resumes: list["TailoredResume"] = Relationship(
        back_populates="base_resume", sa_relationship_kwargs=_SEL
    )
    ats_scores: list["ATSScore"] = Relationship(
        back_populates="resume", sa_relationship_kwargs=_SEL
    )
    applications: list["Application"] = Relationship(
        back_populates="resume", sa_relationship_kwargs=_SEL
    )


# ──────────────────────────────────────────────────────────────────────────
# Jobs
# ──────────────────────────────────────────────────────────────────────────
class Job(TimestampMixin, table=True):
    """A discovered job posting."""

    __tablename__ = "jobs"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    company: str = Field(index=True)
    location: str | None = Field(default=None, index=True)
    salary: str | None = None
    url: str = Field(index=True)
    easy_apply: bool = Field(default=False)
    description: str = ""
    source: JobSource = Field(index=True)
    external_id: str | None = Field(default=None, index=True)  # platform-native job id
    # Stable fingerprint (company + normalised title + url) used for deduplication.
    dedup_hash: str = Field(index=True)
    embedding_id: str | None = Field(default=None, index=True)
    posted_at: datetime | None = None

    applications: list["Application"] = Relationship(
        back_populates="job", sa_relationship_kwargs=_SEL_CASCADE
    )
    ats_scores: list["ATSScore"] = Relationship(
        back_populates="job", sa_relationship_kwargs=_SEL_CASCADE
    )
    tailored_resumes: list["TailoredResume"] = Relationship(
        back_populates="job", sa_relationship_kwargs=_SEL_CASCADE
    )
    cover_letters: list["CoverLetter"] = Relationship(
        back_populates="job", sa_relationship_kwargs=_SEL_CASCADE
    )


# ──────────────────────────────────────────────────────────────────────────
# ATS scoring
# ──────────────────────────────────────────────────────────────────────────
class ATSScore(TimestampMixin, table=True):
    """A weighted ATS evaluation of a resume against a job description.

    Weights (per spec): keyword 30%, skills 25%, experience 20%, education 10%,
    semantic 15%. Sub-scores are 0–100; ``overall_score`` is their weighted sum.
    """

    __tablename__ = "ats_scores"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    resume_id: int | None = Field(default=None, foreign_key="resumes.id", index=True)
    tailored_resume_id: int | None = Field(
        default=None, foreign_key="tailored_resumes.id", index=True
    )

    overall_score: float = 0.0
    keyword_score: float = 0.0
    skills_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    semantic_score: float = 0.0

    missing_keywords: list[str] = json_column()
    matched_keywords: list[str] = json_column()
    strengths: list[str] = json_column()
    weaknesses: list[str] = json_column()
    suggestions: list[str] = json_column()

    model_used: str | None = None

    job: Job = Relationship(back_populates="ats_scores", sa_relationship_kwargs=_SEL)
    resume: Resume | None = Relationship(back_populates="ats_scores", sa_relationship_kwargs=_SEL)
    tailored_resume: Optional["TailoredResume"] = Relationship(sa_relationship_kwargs=_SEL)


# ──────────────────────────────────────────────────────────────────────────
# Tailored resumes
# ──────────────────────────────────────────────────────────────────────────
class TailoredResume(TimestampMixin, table=True):
    """A job-specific, LLM-optimised version of a base resume.

    Content is truthful by construction — derived only from the base resume's
    real experience. A unified ``diff`` and before/after scores capture the change.
    """

    __tablename__ = "tailored_resumes"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    base_resume_id: int = Field(foreign_key="resumes.id", index=True)

    version: int = Field(default=1)
    content: str = ""
    diff: str | None = None  # unified diff: base → tailored
    score_before: float | None = None
    score_after: float | None = None

    # Rendered export artifacts (paths under storage/tailored_resumes).
    pdf_path: str | None = None
    docx_path: str | None = None
    markdown_path: str | None = None
    html_path: str | None = None

    model_used: str | None = None

    job: Job = Relationship(back_populates="tailored_resumes", sa_relationship_kwargs=_SEL)
    base_resume: Resume = Relationship(
        back_populates="tailored_resumes", sa_relationship_kwargs=_SEL
    )


# ──────────────────────────────────────────────────────────────────────────
# Cover letters
# ──────────────────────────────────────────────────────────────────────────
class CoverLetter(TimestampMixin, table=True):
    """A generated cover letter in one of the supported styles."""

    __tablename__ = "cover_letters"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    resume_id: int | None = Field(default=None, foreign_key="resumes.id", index=True)

    style: CoverLetterStyle = Field(default=CoverLetterStyle.concise)
    version: int = Field(default=1)
    content: str = ""

    pdf_path: str | None = None
    docx_path: str | None = None
    markdown_path: str | None = None

    model_used: str | None = None

    job: Job = Relationship(back_populates="cover_letters", sa_relationship_kwargs=_SEL)
    resume: Resume | None = Relationship(sa_relationship_kwargs=_SEL)


# ──────────────────────────────────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────────────────────────────────
class Application(TimestampMixin, table=True):
    """The user's pursuit of a specific job — the central tracking entity."""

    __tablename__ = "applications"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    resume_id: int | None = Field(default=None, foreign_key="resumes.id", index=True)
    tailored_resume_id: int | None = Field(
        default=None, foreign_key="tailored_resumes.id", index=True
    )
    cover_letter_id: int | None = Field(default=None, foreign_key="cover_letters.id", index=True)

    status: ApplicationStatus = Field(default=ApplicationStatus.saved, index=True)
    notes: str = ""
    tags: list[str] = json_column()
    applied_at: datetime | None = None

    job: Job = Relationship(back_populates="applications", sa_relationship_kwargs=_SEL)
    resume: Resume | None = Relationship(back_populates="applications", sa_relationship_kwargs=_SEL)
    tailored_resume: TailoredResume | None = Relationship(sa_relationship_kwargs=_SEL)
    cover_letter: CoverLetter | None = Relationship(sa_relationship_kwargs=_SEL)
    approvals: list["ApprovalWorkflow"] = Relationship(
        back_populates="application", sa_relationship_kwargs=_SEL_CASCADE
    )
    automation_runs: list["AutomationRun"] = Relationship(
        back_populates="application", sa_relationship_kwargs=_SEL_CASCADE
    )


# ──────────────────────────────────────────────────────────────────────────
# Approval workflow (human-in-the-loop)
# ──────────────────────────────────────────────────────────────────────────
class ApprovalWorkflow(TimestampMixin, table=True):
    """A human approval cycle gating an automated submission.

    Snapshots (previews/diff) are stored so the reviewer sees exactly what will be
    submitted. An application is never auto-submitted: a run requires an
    ``approved`` workflow.
    """

    __tablename__ = "approval_workflows"

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    ats_score_id: int | None = Field(default=None, foreign_key="ats_scores.id")
    tailored_resume_id: int | None = Field(default=None, foreign_key="tailored_resumes.id")
    cover_letter_id: int | None = Field(default=None, foreign_key="cover_letters.id")

    state: ApprovalState = Field(default=ApprovalState.generated, index=True)
    resume_preview: str | None = None
    cover_letter_preview: str | None = None
    diff_preview: str | None = None
    reject_reason: str | None = None
    decided_at: datetime | None = None

    application: Application = Relationship(back_populates="approvals", sa_relationship_kwargs=_SEL)
    ats_score: ATSScore | None = Relationship(sa_relationship_kwargs=_SEL)
    tailored_resume: TailoredResume | None = Relationship(sa_relationship_kwargs=_SEL)
    cover_letter: CoverLetter | None = Relationship(sa_relationship_kwargs=_SEL)


# ──────────────────────────────────────────────────────────────────────────
# Browser automation runs
# ──────────────────────────────────────────────────────────────────────────
class AutomationRun(TimestampMixin, table=True):
    """A single browser-automation attempt to submit an application."""

    __tablename__ = "automation_runs"

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    approval_id: int | None = Field(default=None, foreign_key="approval_workflows.id", index=True)

    platform: AutomationPlatform
    status: AutomationStatus = Field(default=AutomationStatus.pending, index=True)
    dry_run: bool = Field(default=False)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)

    screenshots: list[str] = json_column()  # paths under storage/screenshots
    trace_path: str | None = None  # storage/playwright_traces
    error_message: str | None = None
    log: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None

    application: Application = Relationship(
        back_populates="automation_runs", sa_relationship_kwargs=_SEL
    )
    approval: ApprovalWorkflow | None = Relationship(sa_relationship_kwargs=_SEL)


# ──────────────────────────────────────────────────────────────────────────
# LLM usage accounting (powers token/model/latency analytics)
# ──────────────────────────────────────────────────────────────────────────
class LLMUsage(TimestampMixin, table=True):
    """One LLM call's accounting record."""

    __tablename__ = "llm_usage"

    id: int | None = Field(default=None, primary_key=True)
    model: str = Field(index=True)
    operation: str = Field(index=True)  # e.g. "ats_score", "tailor", "cover_letter"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True

    # Optional soft links (no relationship; analytics only).
    job_id: int | None = Field(default=None, index=True)
    application_id: int | None = Field(default=None, index=True)


__all__ = [
    "ATSScore",
    "Application",
    "ApprovalWorkflow",
    "AutomationRun",
    "CoverLetter",
    "Job",
    "LLMUsage",
    "Resume",
    "TailoredResume",
]
