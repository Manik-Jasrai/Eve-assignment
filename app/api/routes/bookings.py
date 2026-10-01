"""Authenticated booking routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.dto.bookings import BookingCreate, BookingDetail, BookingStatus
from app.models.entities import User
from app.services import bookings

router = APIRouter(prefix="/bookings")
SessionDep = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _detail(session: Session, booking: object) -> BookingDetail:
    centre_id, test_id = bookings.booking_context(session, booking)  # type: ignore[arg-type]
    return BookingDetail.model_validate({**{field: getattr(booking, field) for field in BookingDetail.model_fields if field not in {"centre_id", "test_id"}}, "centre_id": centre_id, "test_id": test_id})


@router.post("/", response_model=BookingDetail, status_code=status.HTTP_201_CREATED)
def create(payload: BookingCreate, session: SessionDep, user: CurrentUser) -> BookingDetail:
    return _detail(session, bookings.create_booking(session, user.id, payload.centre_test_id, payload.appointment_at))


@router.get("/")
def list_own(session: SessionDep, user: CurrentUser, booking_status: BookingStatus | None = Query(None, alias="status"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, object]:
    items = [_detail(session, booking) for booking in bookings.list_bookings(session, user.id, booking_status, limit, offset)]
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/{booking_id}/", response_model=BookingDetail)
def detail(booking_id: UUID, session: SessionDep, user: CurrentUser) -> BookingDetail:
    return _detail(session, bookings.get_booking(session, user.id, booking_id))
