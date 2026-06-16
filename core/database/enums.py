"""Enumerations shared across the database models.

All persisted enums are ``StrEnum`` so they store as readable strings in SQLite
and serialise cleanly to JSON in the API layer.
"""

from __future__ import annotations

from enum import StrEnum


class JobSource(StrEnum):
    """Where a job posting was discovered."""

    linkedin = "linkedin"
    indeed = "indeed"
    glassdoor = "glassdoor"
    exa = "exa"
    manual = "manual"


class ApplicationStatus(StrEnum):
    """Lifecycle of a job application (Kanban columns)."""

    saved = "saved"
    interested = "interested"
    tailored = "tailored"
    ready = "ready"
    pending_approval = "pending_approval"
    applied = "applied"
    oa = "oa"  # online assessment
    interview = "interview"
    final_round = "final_round"
    offer = "offer"
    rejected = "rejected"


# Ordered pipeline used by analytics/funnel and Kanban board ordering.
APPLICATION_PIPELINE: tuple[ApplicationStatus, ...] = (
    ApplicationStatus.saved,
    ApplicationStatus.interested,
    ApplicationStatus.tailored,
    ApplicationStatus.ready,
    ApplicationStatus.pending_approval,
    ApplicationStatus.applied,
    ApplicationStatus.oa,
    ApplicationStatus.interview,
    ApplicationStatus.final_round,
    ApplicationStatus.offer,
    ApplicationStatus.rejected,
)


class ApprovalState(StrEnum):
    """Human-in-the-loop approval workflow states."""

    generated = "generated"
    review_required = "review_required"
    approved = "approved"
    applying = "applying"
    applied = "applied"
    rejected = "rejected"


class CoverLetterStyle(StrEnum):
    """Cover letter tone/format presets."""

    concise = "concise"
    startup = "startup"
    enterprise = "enterprise"


class DocumentFormat(StrEnum):
    """Export formats for resumes and cover letters."""

    pdf = "pdf"
    docx = "docx"
    markdown = "markdown"
    html = "html"


class ResumeFileType(StrEnum):
    """Source file type of an uploaded base resume."""

    pdf = "pdf"
    docx = "docx"


class AutomationPlatform(StrEnum):
    """Target platform for browser automation."""

    linkedin = "linkedin"
    indeed = "indeed"
    glassdoor = "glassdoor"


class AutomationStatus(StrEnum):
    """Lifecycle of a browser automation run."""

    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    captcha_detected = "captcha_detected"
    timed_out = "timed_out"
    cancelled = "cancelled"
    dry_run = "dry_run"
