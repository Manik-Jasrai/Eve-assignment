"""Top-level API router composition."""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.catalogue import router as catalogue_router
from app.api.routes.bookings import router as bookings_router
from app.api.routes.payments import router as payments_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(catalogue_router, tags=["catalogue"])
api_router.include_router(bookings_router, tags=["bookings"])
api_router.include_router(payments_router, tags=["payments"])
api_router.include_router(health_router, tags=["health"])
