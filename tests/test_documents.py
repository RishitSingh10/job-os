"""Tests for document export (PDF/DOCX/Markdown/HTML)."""

from __future__ import annotations

from pathlib import Path

import pytest
from core.database.enums import DocumentFormat
from core.documents import export, extension_for, render_html

CONTENT = "# Summary\nSenior engineer.\n\n## Skills\n- Python\n- FastAPI\n"


@pytest.mark.parametrize("fmt", list(DocumentFormat))
def test_export_writes_nonempty_file(tmp_path: Path, fmt: DocumentFormat) -> None:
    path = tmp_path / f"doc.{extension_for(fmt)}"
    returned = export(CONTENT, fmt=fmt, path=path, title="Jane Doe")
    assert returned == path
    assert path.exists()
    assert path.stat().st_size > 0


def test_render_html_escapes_and_structures() -> None:
    html = render_html("Title <x>", "# Heading\n- bullet\nplain & text")
    assert "<title>Title &lt;x&gt;</title>" in html
    assert "<h2>Heading</h2>" in html
    assert "<li>bullet</li>" in html
    assert "plain &amp; text" in html


def test_pdf_has_pdf_header(tmp_path: Path) -> None:
    path = export(CONTENT, fmt=DocumentFormat.pdf, path=tmp_path / "r.pdf", title="R")
    assert path.read_bytes()[:5] == b"%PDF-"
