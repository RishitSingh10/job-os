"""Document processing: render resumes/cover letters to PDF/DOCX/Markdown/HTML.

Parsing of uploaded PDF/DOCX resumes is added alongside upload in a later pass;
this module owns rendering/export.

Public surface::

    from core.documents import export, extension_for, render_html
"""

from core.documents.render import export, extension_for, render_html

__all__ = ["export", "extension_for", "render_html"]
