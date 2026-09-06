"""Database engine and session management.

Sync SQLAlchemy throughout, deliberately — see the Phase 1 architecture
review: this codebase's expensive operations (BM25, FAISS, cross-
encoder, NLI inference) are all CPU-bound and blocking, so mixing an
async DB driver with sync ML inference would add complexity without
benefit. Only the FastAPI route layer is async, and it offloads
blocking calls (including DB access) via a threadpool when needed.

`get_db` is a generator-style dependency for FastAPI's `Depends`,
guaranteeing the session is closed after each request even if the
handler raises.

Database engine and session management.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.database.models import Base


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""
    settings = get_settings()

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=settings.db_pool_size,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
    )


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields and closes a database session."""
    db = get_session_factory()()

    try:
        yield db
    finally:
        db.close()


def init_db(settings: Settings | None = None) -> None:
    """Create missing tables.

    Use Alembic for production schema changes.
    """
    engine = (
        get_engine()
        if settings is None
        else create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    )

    try:
        Base.metadata.create_all(bind=engine)
    finally:
        if settings is not None:
            engine.dispose()