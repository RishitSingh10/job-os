"""Persistence of LLM usage records (powers token/model/latency analytics)."""

from __future__ import annotations

from core.database.crud import CRUDService
from core.database.models import LLMUsage
from core.llm.client import LLMResult


class LLMUsageService(CRUDService[LLMUsage]):
    model = LLMUsage

    async def record(
        self,
        result: LLMResult,
        *,
        operation: str,
        job_id: int | None = None,
        application_id: int | None = None,
        success: bool = True,
    ) -> LLMUsage:
        usage = LLMUsage(
            model=result.model,
            operation=operation,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            latency_ms=result.latency_ms,
            success=success,
            job_id=job_id,
            application_id=application_id,
        )
        return await self.create(usage)
