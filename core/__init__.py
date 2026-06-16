"""Core domain layer for Job OS.

Cross-cutting infrastructure shared by the API and the agents:

* :mod:`core.config`   — strongly-typed settings.
* :mod:`core.logging`  — structured logging.
* :mod:`core.paths`    — storage path management.

Sub-packages (filled in over later phases):

* :mod:`core.database`     — SQLModel engine, session, and models.
* :mod:`core.embeddings`   — ChromaDB-backed vector store.
* :mod:`core.llm`          — Ollama client and prompt orchestration.
* :mod:`core.documents`    — PDF/DOCX parsing and rendering.
* :mod:`core.jobs`         — job discovery, dedup, and indexing services.
* :mod:`core.applications` — application lifecycle and approval services.
* :mod:`core.automation`   — browser automation orchestration.
"""

from core.config import Settings, get_settings
from core.logging import configure_logging, get_logger
from core.paths import StoragePaths, ensure_storage_layout

__all__ = [
    "Settings",
    "StoragePaths",
    "configure_logging",
    "ensure_storage_layout",
    "get_logger",
    "get_settings",
]
