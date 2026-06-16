"""System router — health, readiness, and metadata.

These endpoints have no external dependencies of their own (other than an optional
Ollama probe in readiness), so they are safe to expose from Phase 1 onward and are
used by the frontend and Docker healthchecks.
"""

from __future__ import annotations

import httpx
from core.config import Settings
from core.logging import get_logger
from fastapi import APIRouter, Depends

from backend import __version__
from backend.api.deps import get_app_settings
from backend.api.schemas import DependencyStatus, HealthResponse, ReadinessResponse

log = get_logger(__name__)
router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Return basic liveness and build metadata. Always cheap, never fails."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=__version__,
        environment=settings.environment.value,
    )


async def _probe_ollama(settings: Settings) -> DependencyStatus:
    """Best-effort check that the local Ollama runtime is reachable."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/version"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        version = resp.json().get("version", "unknown")
        return DependencyStatus(name="ollama", ok=True, detail=f"version {version}")
    except (httpx.HTTPError, ValueError) as exc:
        return DependencyStatus(name="ollama", ok=False, detail=str(exc))


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def ready(settings: Settings = Depends(get_app_settings)) -> ReadinessResponse:
    """Aggregate readiness of optional external dependencies.

    Readiness is informational in local-first mode: a missing Ollama runtime does
    not crash the app, it simply reports ``ready=False`` so the UI can warn the user.
    """
    deps = [await _probe_ollama(settings)]
    return ReadinessResponse(ready=all(d.ok for d in deps), dependencies=deps)
