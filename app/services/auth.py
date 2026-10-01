"""Minimal authentication business logic and JWT helpers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, ConflictError
from app.models.entities import User


_password_hash = PasswordHash.recommended()
# This constant is deliberately generated at module initialization instead of
# per request, so an unknown account still incurs a real Argon2 verification.
_dummy_password_hash = _password_hash.hash("not-a-real-user-password")


def register_user(session: Session, *, email: str, password: str) -> User:
    """Persist one account for a normalized email address."""
    user = User(email=email, password_hash=_password_hash.hash(password))
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except IntegrityError as exc:
        session.rollback()
        if "uq_users_email_normalized" in str(exc.orig):
            raise ConflictError("An account with this email already exists") from exc
        raise
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    """Verify credentials without revealing whether an email is registered."""
    user = session.scalar(select(User).where(User.email == email))
    password_hash = user.password_hash if user is not None else _dummy_password_hash
    if not _password_hash.verify(password, password_hash) or user is None:
        raise AuthenticationError("Invalid email or password")
    return user


def create_access_token(user_id: UUID, settings: Settings | None = None) -> tuple[str, int]:
    """Create a short-lived bearer JWT and return its lifetime in seconds."""
    settings = settings or get_settings()
    now = datetime.now(UTC)
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256"), expires_in


def decode_subject(token: str, settings: Settings | None = None) -> UUID:
    """Validate a token fully and return its UUID subject."""
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, ValueError, KeyError) as exc:
        raise AuthenticationError("Invalid or expired access token") from exc


def get_authenticated_user(session: Session, user_id: UUID) -> User:
    """Resolve a JWT subject on every authenticated request."""
    user = session.get(User, user_id)
    if user is None:
        raise AuthenticationError("Invalid or expired access token")
    return user
