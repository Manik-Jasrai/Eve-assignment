"""Shared FastAPI dependencies for protected routes."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.db.session import get_db_session
from app.models.entities import User
from app.services.auth import decode_subject, get_authenticated_user


_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[Session, Depends(get_db_session)],
) -> User:
    """Return the current JWT-authenticated user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    return get_authenticated_user(session, decode_subject(credentials.credentials))
