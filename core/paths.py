"""Storage path management.

Centralises every on-disk location the application writes to. The layout mirrors
the ``storage/`` tree described in the project spec. :func:`ensure_storage_layout`
is called once on startup so every directory exists before any agent touches it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class StoragePaths:
    """Resolved, absolute paths for every storage sub-directory.

    Construct via :meth:`from_settings`; never hard-code storage paths elsewhere.
    """

    root: Path
    base_resumes: Path
    tailored_resumes: Path
    cover_letters: Path
    screenshots: Path
    browser_profiles: Path
    exports: Path
    logs: Path
    playwright_traces: Path
    chroma: Path

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> StoragePaths:
        settings = settings or get_settings()
        root = settings.storage_root
        return cls(
            root=root,
            base_resumes=root / "base_resumes",
            tailored_resumes=root / "tailored_resumes",
            cover_letters=root / "cover_letters",
            screenshots=root / "screenshots",
            browser_profiles=root / "browser_profiles",
            exports=root / "exports",
            logs=root / "logs",
            playwright_traces=root / "playwright_traces",
            chroma=settings.chroma_dir,
        )

    def all_dirs(self) -> tuple[Path, ...]:
        return (
            self.root,
            self.base_resumes,
            self.tailored_resumes,
            self.cover_letters,
            self.screenshots,
            self.browser_profiles,
            self.exports,
            self.logs,
            self.playwright_traces,
            self.chroma,
        )

    def ensure(self) -> StoragePaths:
        """Create every storage directory (idempotent). Returns self for chaining."""
        for directory in self.all_dirs():
            directory.mkdir(parents=True, exist_ok=True)
        return self


def ensure_storage_layout(settings: Settings | None = None) -> StoragePaths:
    """Convenience wrapper: build :class:`StoragePaths` and create all directories."""
    return StoragePaths.from_settings(settings).ensure()
