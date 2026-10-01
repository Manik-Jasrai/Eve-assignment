"""Lazy synchronous SQLAlchemy session setup."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create the database engine only when persistence is first used."""
    return create_engine(
        str(get_settings().database_url),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the request-session factory."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yield and close a session; write services will own transactions later."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
