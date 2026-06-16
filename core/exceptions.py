"""Domain-level exceptions.

These live in the core layer so services can raise meaningful errors without
knowing anything about HTTP. The API layer (``backend.api.errors``) maps them to
status codes.
"""

from __future__ import annotations


class JobOSError(Exception):
    """Base class for all application domain errors."""


class EntityNotFoundError(JobOSError):
    """A requested entity does not exist."""

    def __init__(self, entity: str, entity_id: object) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id {entity_id!r} was not found")


class ValidationError(JobOSError):
    """A domain invariant was violated (maps to HTTP 422/400)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConflictError(JobOSError):
    """An operation conflicts with existing state (maps to HTTP 409)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
