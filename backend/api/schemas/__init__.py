"""API request/response schemas, grouped by feature.

Re-exports the common and system schemas so existing imports
(``from backend.api.schemas import HealthResponse``) keep working.
"""

from backend.api.schemas.common import Message, Page
from backend.api.schemas.system import DependencyStatus, HealthResponse, ReadinessResponse

__all__ = [
    "DependencyStatus",
    "HealthResponse",
    "Message",
    "Page",
    "ReadinessResponse",
]
