"""Embeddings + vector store (ChromaDB + nomic-embed-text via Ollama).

Public surface::

    from core.embeddings import Embedder, OllamaEmbedder, DeterministicEmbedder
    from core.embeddings import VectorStore, SimilarHit, try_create_vector_store
"""

from core.embeddings.embedder import DeterministicEmbedder, Embedder, OllamaEmbedder
from core.embeddings.store import (
    SimilarHit,
    VectorStore,
    chromadb_available,
    try_create_vector_store,
)

__all__ = [
    "DeterministicEmbedder",
    "Embedder",
    "OllamaEmbedder",
    "SimilarHit",
    "VectorStore",
    "chromadb_available",
    "try_create_vector_store",
]
