"""ChromaDB-backed vector store.

Wraps a persistent ChromaDB collection for similarity search over job (and later
resume) embeddings. ChromaDB is imported lazily so the application still boots if
the optional ``embeddings`` extra is not installed — callers can check
:func:`chromadb_available` and degrade gracefully.

ChromaDB's client is synchronous; calls are offloaded to a worker thread so they
don't block the event loop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from anyio import to_thread

from core.config import Settings, get_settings
from core.logging import get_logger

log = get_logger(__name__)


def _ensure_protobuf_pure() -> None:
    """Force protobuf's pure-Python backend before chromadb (hence protobuf) loads.

    Avoids the "Descriptors cannot be created directly" crash from a C-extension
    protobuf that is newer than chromadb's generated descriptors.
    """
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def chromadb_available() -> bool:
    try:
        _ensure_protobuf_pure()
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass(frozen=True, slots=True)
class SimilarHit:
    """One nearest-neighbour result."""

    id: str
    distance: float  # cosine distance in [0, 2]; lower = more similar
    metadata: dict[str, Any]


class VectorStore:
    """A persistent ChromaDB collection (cosine space)."""

    def __init__(self, settings: Settings | None = None, *, collection: str | None = None) -> None:
        _ensure_protobuf_pure()
        import chromadb  # lazy: only required when the store is actually used

        self._settings = settings or get_settings()
        self._settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._settings.chroma_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection or self._settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        await to_thread.run_sync(
            lambda: self._collection.upsert(
                ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
            )
        )

    async def query(self, embedding: list[float], *, n_results: int = 5) -> list[SimilarHit]:
        result = await to_thread.run_sync(
            lambda: self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["distances", "metadatas"],
            )
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        return [
            SimilarHit(id=i, distance=float(d), metadata=m or {})
            for i, d, m in zip(ids, distances, metadatas, strict=False)
        ]

    async def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        await to_thread.run_sync(lambda: self._collection.delete(ids=ids))

    async def count(self) -> int:
        return await to_thread.run_sync(self._collection.count)


def try_create_vector_store(settings: Settings | None = None) -> VectorStore | None:
    """Build a :class:`VectorStore`, or return ``None`` if unavailable.

    Never raises: a missing ``embeddings`` extra or a Chroma init error simply
    disables semantic features rather than crashing startup.
    """
    if not chromadb_available():
        log.warning("vector_store_unavailable", reason="chromadb not installed")
        return None
    try:
        return VectorStore(settings)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("vector_store_unavailable", reason=str(exc))
        return None
