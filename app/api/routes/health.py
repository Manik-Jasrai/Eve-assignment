"""Public process health endpoints."""

from fastapi import APIRouter

from app.core.errors import ServiceUnavailableError
from app.db.readiness import database_is_reachable, database_is_ready

router = APIRouter()


@router.get("/health/", summary="Get service metadata")
def health() -> dict[str, str]:
    """Return metadata without requiring database availability."""
    return {"service": "eve-diagnostic-booking-api", "version": "0.1.0"}


@router.get("/health/live/", summary="Check whether the process is live")
def live() -> dict[str, str]:
    """Confirm that the application process can serve requests."""
    return {"status": "ok"}


@router.get("/health/db/", summary="Check database connectivity")
def database_health() -> dict[str, str]:
    """Confirm the application can reach PostgreSQL without requiring migrations."""
    if not database_is_reachable():
        raise ServiceUnavailableError("Database is unavailable")
    return {"status": "ok"}


@router.get("/health/ready/", summary="Check database and schema readiness")
def ready() -> dict[str, str]:
    """Confirm the database accepts a bounded query and is at the expected revision."""
    if not database_is_ready():
        raise ServiceUnavailableError("Service is not ready")
    return {"status": "ok"}
