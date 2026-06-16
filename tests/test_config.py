"""Tests for configuration and storage path management."""

from __future__ import annotations

from pathlib import Path

from core.config import Environment, Settings
from core.paths import StoragePaths, ensure_storage_layout


def test_relative_storage_paths_resolve_to_absolute(tmp_path: Path) -> None:
    settings = Settings(storage_root=Path("storage"), chroma_dir=Path("storage/chroma"))
    assert settings.storage_root.is_absolute()
    assert settings.chroma_dir.is_absolute()


def test_environment_helpers() -> None:
    assert Settings(environment=Environment.production).is_production is True
    assert Settings(environment=Environment.test).is_test is True
    assert Settings(environment=Environment.development).is_production is False


def test_ensure_storage_layout_creates_all_dirs(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        chroma_dir=tmp_path / "storage" / "chroma",
    )
    paths = ensure_storage_layout(settings)

    assert isinstance(paths, StoragePaths)
    for directory in paths.all_dirs():
        assert directory.exists(), f"expected {directory} to exist"
        assert directory.is_dir()


def test_storage_paths_layout_matches_spec(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "s", chroma_dir=tmp_path / "s" / "chroma")
    paths = StoragePaths.from_settings(settings)

    assert paths.base_resumes.name == "base_resumes"
    assert paths.tailored_resumes.name == "tailored_resumes"
    assert paths.cover_letters.name == "cover_letters"
    assert paths.screenshots.name == "screenshots"
    assert paths.browser_profiles.name == "browser_profiles"
    assert paths.exports.name == "exports"
    assert paths.logs.name == "logs"
    assert paths.playwright_traces.name == "playwright_traces"
