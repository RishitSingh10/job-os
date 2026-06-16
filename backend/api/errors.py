"""Mapping of core domain exceptions to HTTP responses.

Keeping this in the API layer means the core/services layer can raise plain domain
errors without importing FastAPI. :func:`register_exception_handlers` is called by
the app factory.
"""

from __future__ import annotations

from core.exceptions import ConflictError, EntityNotFoundError, ValidationError
from core.logging import get_logger
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

log = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundError)
    async def _not_found(_: Request, exc: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.message}
        )

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})
