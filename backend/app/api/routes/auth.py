"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_database
from app.api.schemas.auth import (
    AuthResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.database.models import User
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def _get_auth_service(db: Session) -> AuthService:
    """Create an authentication service for the current DB session."""
    return AuthService(db)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_database),
) -> AuthResponse:
    """Register a new user and create an authenticated session."""

    service = _get_auth_service(db)

    try:
        user = service.register_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )

        access_token, refresh_token = service.create_session(
            user=user,
            user_agent=request.headers.get("user-agent"),
            ip_address=(
                request.client.host
                if request.client is not None
                else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    payload: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_database),
) -> AuthResponse:
    """Authenticate an existing user and create a session."""

    service = _get_auth_service(db)

    user = service.authenticate_user(
        email=payload.email,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = service.create_session(
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=(
            request.client.host
            if request.client is not None
            else None
        ),
    )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def refresh(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_database),
) -> TokenResponse:
    """Rotate a refresh token and issue a new token pair."""

    service = _get_auth_service(db)

    tokens = service.refresh_session(
        refresh_token=payload.refresh_token,
    )

    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    access_token, refresh_token = tokens

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_database),
) -> None:
    """Revoke the supplied refresh token."""

    service = _get_auth_service(db)

    service.revoke_refresh_token(
        refresh_token=payload.refresh_token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user."""

    return UserResponse.model_validate(current_user)