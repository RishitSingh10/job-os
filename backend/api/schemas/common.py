"""Shared API schemas: pagination envelope and simple messages."""

from __future__ import annotations

from pydantic import BaseModel


class Page[T](BaseModel):
    """A paginated list response."""

    items: list[T]
    total: int
    offset: int
    limit: int


class Message(BaseModel):
    """A simple detail message (used for deletes and errors)."""

    detail: str
