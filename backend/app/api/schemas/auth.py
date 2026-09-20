"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload used to create a new user account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    full_name: str | None = Field(
        default=None,
        max_length=150,
    )


class UserLoginRequest(BaseModel):
    """Credentials supplied during login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token supplied to obtain a new session."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(
        min_length=1,
    )


class LogoutRequest(BaseModel):
    """Refresh token supplied during logout."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(
        min_length=1,
    )


class UserResponse(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None


class TokenResponse(BaseModel):
    """Authentication tokens returned to the client."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Authentication response containing user and tokens."""

    user: UserResponse
    tokens: TokenResponse