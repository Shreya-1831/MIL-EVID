"""Authentication service for MIL-EVID."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database.models import RefreshToken, User


class AuthService:
    """Handle user registration, authentication, and sessions."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def register_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Create a new user account."""

        normalized_email = email.strip().lower()

        existing_user = self.get_user_by_email(
            normalized_email,
        )

        if existing_user is not None:
            raise ValueError(
                "A user with this email address already exists."
            )

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            full_name=(
                full_name.strip()
                if full_name and full_name.strip()
                else None
            ),
            is_active=True,
            is_verified=False,
        )

        self._db.add(user)

        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise ValueError(
                "A user with this email address already exists."
            ) from None

        self._db.refresh(user)

        return user

    def authenticate_user(
        self,
        *,
        email: str,
        password: str,
    ) -> User | None:
        """Authenticate a user using email and password."""

        user = self.get_user_by_email(
            email.strip().lower(),
        )

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        user.last_login_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(user)

        return user

    def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        """Find a user by normalized email address."""

        statement = select(User).where(
            User.email == email.strip().lower()
        )

        return self._db.scalar(statement)

    def get_user_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        """Find a user by UUID."""

        statement = select(User).where(
            User.id == user_id
        )

        return self._db.scalar(statement)

    def create_session(
        self,
        *,
        user: User,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        """Create access and refresh tokens for a user."""

        access_token = create_access_token(
            subject=str(user.id),
        )

        refresh_token = generate_refresh_token()

        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(
                refresh_token,
            ),
            expires_at=get_refresh_token_expiry(),
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self._db.add(refresh_token_record)
        self._db.commit()

        return access_token, refresh_token

    def refresh_session(
        self,
        *,
        refresh_token: str,
    ) -> tuple[str, str] | None:
        """Rotate a refresh token and issue a new session."""

        token_hash = hash_refresh_token(
            refresh_token,
        )

        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
        )

        stored_token = self._db.scalar(statement)

        if stored_token is None:
            return None

        now = datetime.utcnow()

        if stored_token.revoked_at is not None:
            return None

        if stored_token.expires_at <= now:
            return None

        user = self.get_user_by_id(
            stored_token.user_id,
        )

        if user is None or not user.is_active:
            return None

        # Rotate the refresh token.
        stored_token.revoked_at = now

        new_access_token = create_access_token(
            subject=str(user.id),
        )

        new_refresh_token = generate_refresh_token()

        new_refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(
                new_refresh_token,
            ),
            expires_at=get_refresh_token_expiry(),
            user_agent=stored_token.user_agent,
            ip_address=stored_token.ip_address,
        )

        self._db.add(new_refresh_record)
        self._db.commit()

        return new_access_token, new_refresh_token

    def revoke_refresh_token(
        self,
        *,
        refresh_token: str,
    ) -> bool:
        """Revoke a refresh token."""

        token_hash = hash_refresh_token(
            refresh_token,
        )

        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
        )

        stored_token = self._db.scalar(statement)

        if stored_token is None:
            return False

        if stored_token.revoked_at is not None:
            return False

        stored_token.revoked_at = datetime.utcnow()

        self._db.commit()

        return True

    def revoke_all_user_sessions(
        self,
        *,
        user_id: UUID,
    ) -> int:
        """Revoke all active refresh tokens for a user."""

        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )

        tokens = self._db.scalars(statement).all()

        if not tokens:
            return 0

        now = datetime.utcnow()

        for token in tokens:
            token.revoked_at = now

        self._db.commit()

        return len(tokens)