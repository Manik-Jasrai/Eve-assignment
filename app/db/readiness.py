"""Bounded database and schema readiness checks."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import get_engine


def database_is_reachable() -> bool:
    """Return whether the configured database accepts a short ``SELECT 1`` query."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    except SQLAlchemyError:
        return False


def database_is_ready() -> bool:
    """Check database connectivity and the exact migration revision without leaking DB details."""
    expected_revision = get_settings().alembic_expected_revision
    if not expected_revision:
        return False

    try:
        with get_engine().connect() as connection:
            # This applies only to this short transaction, keeping normal queries
            # independent from readiness-probe limits.
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            connection.execute(text("SELECT 1")).scalar_one()
            current_revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
    except SQLAlchemyError:
        return False

    return current_revision == expected_revision
