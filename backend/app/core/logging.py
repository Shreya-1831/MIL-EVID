"""Structured logging configuration.

MIL-EVID uses `structlog` so log lines are structured key/value data
rather than free-form strings. This makes it possible to trace a
single analysis request across query analysis, retrieval, and
verification without grepping through prose.

Call `configure_logging()` once at application startup (this is done
in `app.main` via the FastAPI lifespan). Modules should obtain a
logger with `get_logger(__name__)` and never use `print`.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure stdlib logging + structlog for the whole process.

    Idempotent: safe to call more than once (e.g. once from
    application startup and once from a test fixture).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the given module name."""
    return structlog.get_logger(name)
