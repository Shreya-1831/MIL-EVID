"""Health check endpoint.

Deliberately has no dependency on models, indexes, or the database —
it should answer even if downstream components are still loading, so
it's safe to use as a liveness probe. A separate readiness check can
be added later (Phase 10) once model/index loading exists.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(
    tags=["health"],
)


class HealthResponse(BaseModel):
    status: str = "ok"


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    """Liveness check. Always returns 200 if the process is running."""

    return HealthResponse(
        status="ok",
    )