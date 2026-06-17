"""LLM client abstraction over local Ollama.

One :class:`LLMClient` protocol with two implementations:

* :class:`OllamaClient` — real text generation from a local Ollama model.
* :class:`StubLLMClient` — deterministic, offline client for tests (returns fixed
  text or a caller-provided responder), so the tailoring/cover-letter agents can be
  exercised without a running model.

Every call returns an :class:`LLMResult` carrying token counts and latency, which
the agents persist as :class:`~core.database.models.LLMUsage` for analytics.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol, runtime_checkable

import httpx

from core.config import Settings, get_settings


@dataclass(slots=True)
class LLMResult:
    """The text and accounting metadata for one generation call."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@runtime_checkable
class LLMClient(Protocol):
    """Generates text from a prompt (+ optional system instruction)."""

    model: str

    async def generate(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.4
    ) -> LLMResult: ...


class OllamaClient:
    """Text generation via a local Ollama model's ``/api/generate`` endpoint."""

    def __init__(self, settings: Settings | None = None, *, model: str | None = None) -> None:
        self._settings = settings or get_settings()
        self.model = model or self._settings.llm_default_model
        self._base_url = self._settings.ollama_base_url.rstrip("/")

    async def generate(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.4
    ) -> LLMResult:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        start = perf_counter()
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self._base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        latency_ms = round((perf_counter() - start) * 1000, 1)

        return LLMResult(
            text=(data.get("response") or "").strip(),
            model=self.model,
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            latency_ms=latency_ms,
        )


class StubLLMClient:
    """Deterministic offline client for tests and dry runs."""

    model = "stub"

    def __init__(
        self,
        *,
        text: str | None = None,
        responder: Callable[[str, str | None], str] | None = None,
    ) -> None:
        self._text = text
        self._responder = responder

    async def generate(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.4
    ) -> LLMResult:
        if self._responder is not None:
            text = self._responder(prompt, system)
        elif self._text is not None:
            text = self._text
        else:
            text = prompt  # echo
        return LLMResult(
            text=text,
            model=self.model,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            latency_ms=0.0,
        )
