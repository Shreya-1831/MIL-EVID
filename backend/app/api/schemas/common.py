"""Common API response schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard API error response."""

    error: str
    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated API response."""

    items: list[T] = Field(default_factory=list)
    total: int
    limit: int
    offset: int