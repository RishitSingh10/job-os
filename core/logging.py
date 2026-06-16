"""Structured logging configuration.

Uses ``structlog`` for structured, context-rich logs. Two sinks are configured:

* **Console** — human-friendly (or JSON, if ``log_json`` is set) for live dev output.
* **File** — always JSON Lines, written to ``storage/logs/jobos.jsonl`` for the
  local audit trail required by the spec (no external monitoring).

Call :func:`configure_logging` once during application startup, then obtain
loggers anywhere with :func:`get_logger`.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Any

import structlog

from core.config import Settings, get_settings
from core.paths import StoragePaths

_configured: bool = False

# Processors shared by every structlog logger before it is routed to stdlib logging.
_SHARED_PROCESSORS: list[structlog.types.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]


def _build_file_handler(logs_dir: Path) -> logging.Handler:
    """A rotating JSONL file handler for the persistent audit trail."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        logs_dir / "jobos.jsonl",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=_SHARED_PROCESSORS,
        )
    )
    return handler


def _build_console_handler(*, json_output: bool) -> logging.Handler:
    handler = logging.StreamHandler()
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=_SHARED_PROCESSORS,
        )
    )
    return handler


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog + stdlib logging. Idempotent across calls."""
    global _configured
    if _configured:
        return

    settings = settings or get_settings()
    paths = StoragePaths.from_settings(settings)
    level = logging.getLevelName(settings.log_level.value)

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(_build_console_handler(json_output=settings.log_json))
    root.addHandler(_build_file_handler(paths.logs))

    # Tame noisy third-party loggers.
    for noisy in ("uvicorn.access", "watchfiles", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str | None = None, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger, optionally pre-bound with context values."""
    logger = structlog.get_logger(name)
    return logger.bind(**initial_values) if initial_values else logger


def reset_logging_for_tests() -> None:
    """Reset the one-time guard so tests can reconfigure logging deterministically."""
    global _configured
    _configured = False
