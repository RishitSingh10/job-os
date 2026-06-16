"""FastAPI dependency providers.

Centralises request-scoped dependencies. ``get_app_settings`` resolves the
:class:`Settings` instance that the app was *constructed* with (stored on
``app.state``), rather than the process-global cached settings. This keeps the app
testable: ``create_app(test_settings)`` fully controls configuration for that
instance.
"""

from __future__ import annotations

from core.config import Settings
from fastapi import Request


def get_app_settings(request: Request) -> Settings:
    """Return the :class:`Settings` bound to the running application instance."""
    return request.app.state.settings
