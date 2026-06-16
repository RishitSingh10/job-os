"""Discovery router — trigger a discovery/import run for a source."""

from __future__ import annotations

from typing import Annotated

from agents.discovery import DiscoveryAgent
from agents.discovery.adapters import ExaAdapter, JobPosting, JobSourceAdapter, ManualAdapter
from core.config import Settings
from core.database.enums import JobSource
from core.embeddings import Embedder, VectorStore
from core.exceptions import ValidationError
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_app_settings, get_embedder, get_session, get_vector_store
from backend.api.schemas.discovery import DiscoveryRunRequest, DiscoveryRunResponse

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
VectorStoreDep = Annotated["VectorStore | None", Depends(get_vector_store)]

# Live scraping of these arrives in Phase 9 (browser automation).
_BROWSER_SOURCES = {JobSource.linkedin, JobSource.indeed, JobSource.glassdoor}


def _build_adapter(req: DiscoveryRunRequest, settings: Settings) -> JobSourceAdapter:
    if req.source == JobSource.manual:
        if not req.postings:
            raise ValidationError("Manual discovery requires a non-empty 'postings' list.")
        postings = [JobPosting(**p.model_dump(), source=JobSource.manual) for p in req.postings]
        return ManualAdapter(postings)
    if req.source == JobSource.exa:
        return ExaAdapter(settings)
    if req.source in _BROWSER_SOURCES:
        raise ValidationError(
            f"Live {req.source.value} discovery arrives in Phase 9 (browser automation). "
            "Use 'manual' to import postings now."
        )
    raise ValidationError(f"Unsupported source: {req.source.value}")


@router.post("/run", response_model=DiscoveryRunResponse)
async def run_discovery(
    req: DiscoveryRunRequest,
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    vector_store: VectorStoreDep,
) -> DiscoveryRunResponse:
    adapter = _build_adapter(req, settings)
    agent = DiscoveryAgent(session, embedder=embedder, vector_store=vector_store)
    result = await agent.discover(adapter, req.query, limit=req.limit, dry_run=req.dry_run)
    return DiscoveryRunResponse(
        source=result.source,
        query=result.query,
        fetched=result.fetched,
        created=result.created,
        duplicates=result.duplicates,
        indexed=result.indexed,
        semantic_enabled=result.semantic_enabled,
        created_job_ids=result.created_job_ids,
    )
