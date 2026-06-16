"""Application configuration.

A single, strongly-typed :class:`Settings` object is the source of truth for all
runtime configuration. Values are loaded (in order of precedence) from the process
environment, then a local ``.env`` file, then the defaults declared here.

Access the settings through :func:`get_settings`, which is cached so the ``.env``
file is read only once per process.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = the directory that contains this `core/` package's parent.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Environment(StrEnum):
    """Deployment environment."""

    development = "development"
    production = "production"
    test = "test"


class LogLevel(StrEnum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Strongly-typed application settings.

    All fields are overridable via ``JOBOS_``-prefixed environment variables
    (see ``.env.example``).
    """

    model_config = SettingsConfigDict(
        env_prefix="JOBOS_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "Job OS"
    environment: Environment = Environment.development
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000

    # --- CORS ---
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Storage ---
    storage_root: Path = Path("storage")

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///jobos.db"

    # --- Logging ---
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = False

    # --- Ollama / LLM ---
    ollama_base_url: str = "http://localhost:11434"
    llm_default_model: str = "qwen3"
    llm_coder_model: str = "qwen2.5-coder"
    llm_fallback_model: str = "mistral-small"
    embedding_model: str = "nomic-embed-text"

    # --- ChromaDB ---
    chroma_dir: Path = Path("storage/chroma")
    chroma_collection: str = "jobos"

    # --- External APIs ---
    exa_api_key: str | None = None

    @field_validator("storage_root", "chroma_dir")
    @classmethod
    def _resolve_relative_to_root(cls, value: Path) -> Path:
        """Resolve relative storage paths against the project root, not the CWD."""
        path = Path(value)
        return path if path.is_absolute() else (PROJECT_ROOT / path)

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.production

    @property
    def is_test(self) -> bool:
        return self.environment is Environment.test


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance."""
    return Settings()
