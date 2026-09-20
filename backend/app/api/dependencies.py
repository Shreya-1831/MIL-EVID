"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.models import User
from app.database.session import get_db, get_session_factory
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisService


_bearer_scheme = HTTPBearer(auto_error=False)


def get_database() -> Iterator[Session]:
    """Provide a database session for the current request."""
    yield from get_db()


def get_analysis_repository(
    db: Session = Depends(get_database),
) -> AnalysisRepository:
    """Return the analysis repository for the current request."""
    return AnalysisRepository(db)


def get_analysis_service(
    request: Request,
) -> AnalysisService:
    """Return the application-wide MIL-EVID analysis service."""
    service = getattr(request.app.state, "analysis_service", None)

    if service is None:
        raise RuntimeError(
            "AnalysisService has not been initialized."
        )

    return service


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        _bearer_scheme
    ),
) -> User:
    """Return the authenticated user from the access token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    db = get_session_factory()()

    try:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is unavailable.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    finally:
        db.close()