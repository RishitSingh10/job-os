"""Tests for the LLM client stub and usage accounting."""

from __future__ import annotations

from core.database import Database
from core.llm import LLMUsageService, StubLLMClient


async def test_stub_echoes_and_counts_tokens() -> None:
    stub = StubLLMClient()
    result = await stub.generate("hello world from prompt")
    assert result.text == "hello world from prompt"
    assert result.prompt_tokens == 4
    assert result.total_tokens == result.prompt_tokens + result.completion_tokens


async def test_stub_responder_receives_prompt_and_system() -> None:
    stub = StubLLMClient(responder=lambda p, s: f"sys={s}|p={p}")
    result = await stub.generate("PROMPT", system="SYS")
    assert result.text == "sys=SYS|p=PROMPT"


async def test_usage_service_records(db: Database) -> None:
    async with db.session() as session:
        svc = LLMUsageService(session)
        stub = StubLLMClient(text="some generated text here")
        result = await stub.generate("a prompt")
        usage = await svc.record(result, operation="tailor", job_id=7)

        assert usage.id is not None
        assert usage.operation == "tailor"
        assert usage.job_id == 7
        assert usage.total_tokens == result.total_tokens
        assert usage.model == "stub"
