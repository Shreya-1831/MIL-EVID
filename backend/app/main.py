"""MIL-EVID FastAPI application entry point.

This module is responsible only for wiring: creating the FastAPI app,
configuring logging, registering the exception-handling policy, and
including routers. It must not contain business logic — that lives in
`app/modules` and is orchestrated by `app/services/pipeline.py`.

Model and index loading (embedding model, cross-encoder, NLI model,
FAISS/BM25 indexes) will be added to the `lifespan` context manager in
later phases, so they are constructed once at startup and attached to
`app.state` rather than being recreated per-request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    DynamicEvidenceError,
    MilEvidError,
    PipelineError,
    QueryAnalysisError,
    RetrievalError,
)
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

# Maps exception types to HTTP status codes for the centralized
# exception handler below. Checked in order, most specific first,
# since Python's exception hierarchy means a subclass would otherwise
# match its parent's entry.
_STATUS_CODE_MAP: tuple[tuple[type[MilEvidError], int], ...] = (
    (ConfigurationError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    (QueryAnalysisError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (DynamicEvidenceError, status.HTTP_502_BAD_GATEWAY),
    (RetrievalError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    (PipelineError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    (MilEvidError, status.HTTP_500_INTERNAL_SERVER_ERROR),
)


def _status_code_for(exc: MilEvidError) -> int:
    for exc_type, code in _STATUS_CODE_MAP:
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_500_INTERNAL_SERVER_ERROR


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown.

    Phase 1 only validates configuration and configures logging.
    Later phases attach long-lived resources (embedding model,
    cross-encoder, NLI model, BM25/FAISS indexes, DB engine) to
    `app.state` here so they are loaded exactly once per process.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        environment=settings.environment,
        acled_configured=settings.acled_configured,
    )

    yield

    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Application factory.

    Using a factory (rather than a bare module-level `app = FastAPI()`)
    keeps startup side effects out of import time, which makes the app
    easier to test with different settings.
    """
    app = FastAPI(
        title="MIL-EVID",
        description=(
            "Static-Dynamic Evidence-Grounded Hybrid RAG for "
            "multi-perspective military situation analysis."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(MilEvidError)
    async def mil_evid_exception_handler(
        request: Request, exc: MilEvidError
    ) -> JSONResponse:
        """Central mapping from domain exceptions to HTTP responses.

        Every deliberately-raised MIL-EVID exception is caught here so
        individual routes don't need repetitive try/except blocks.
        Unexpected (non-`MilEvidError`) exceptions are intentionally
        left to FastAPI's default handler, which logs a full traceback
        and returns a generic 500 — swallowing unknown errors here
        would hide bugs.
        """
        logger.error(
            "request_failed",
            path=str(request.url.path),
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return JSONResponse(
            status_code=_status_code_for(exc),
            content={"error": type(exc).__name__, "detail": str(exc)},
        )

    app.include_router(health_router)

    return app


app = create_app()
