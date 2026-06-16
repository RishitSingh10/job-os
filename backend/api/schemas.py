"""Shared API response schemas.

Phase-1 schemas describe the system/health endpoints. Feature schemas live next
to their routers in later phases.
"""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness/readiness payload returned by ``GET /api/health``."""

    status: str
    app_name: str
    version: str
    environment: str


class DependencyStatus(BaseModel):
    """Status of a single external dependency (e.g. Ollama, ChromaDB)."""

    name: str
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    """Aggregated readiness across optional external dependencies."""

    ready: bool
    dependencies: list[DependencyStatus]
