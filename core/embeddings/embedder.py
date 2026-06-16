"""Text embedding providers.

Two implementations behind one :class:`Embedder` protocol:

* :class:`OllamaEmbedder` — real embeddings from a local Ollama model
  (``nomic-embed-text`` by default).
* :class:`DeterministicEmbedder` — a dependency-free, offline bag-of-words
  hashing embedder. Identical text yields identical vectors and near-identical
  text yields near vectors, which is enough for deterministic dedup tests and a
  graceful fallback when Ollama is unreachable.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

import httpx

from core.config import Settings, get_settings
from core.logging import get_logger

log = get_logger(__name__)

_WORD = re.compile(r"[a-z0-9]+")


@runtime_checkable
class Embedder(Protocol):
    """Produces unit-norm embedding vectors for a batch of texts."""

    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_one(self, text: str) -> list[float]: ...


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


class DeterministicEmbedder:
    """Offline hashing embedder: deterministic, no network, no extra deps."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _vectorize(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        for token in _WORD.findall(text.lower()):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[bucket] += sign
        return _l2_normalize(vec)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return self._vectorize(text)


class OllamaEmbedder:
    """Embeddings from a local Ollama model via its HTTP API."""

    def __init__(self, settings: Settings | None = None, *, dimensions: int = 768) -> None:
        self._settings = settings or get_settings()
        self._model = self._settings.embedding_model
        self._base_url = self._settings.ollama_base_url.rstrip("/")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError("Ollama returned no embeddings")
        self._dimensions = len(embeddings[0])
        return [_l2_normalize(e) for e in embeddings]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]
