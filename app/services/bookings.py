"""Booking creation, snapshots, and owner-scoped retrieval."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.entities import Booking, Centre, CentreTest, DiagnosticTest


def _locked(session: Session, model: type[object], record_id: UUID) -> object | None:
    if hasattr(session, "lock"):
        return session.lock(model, record_id)  # type: ignore[attr-defined]
    return session.execute(select(model).where(model.id == record_id).with_for_update()).scalar_one_or_none()  # type: ignore[attr-defined]


def create_booking(session: Session, user_id: UUID, centre_test_id: UUID, appointment_at: datetime, now: datetime | None = None) -> Booking:
    current_time = now or datetime.now(UTC)
    if appointment_at <= current_time:
        raise BusinessRuleError("appointment_at must be in the future")
    offering = _locked(session, CentreTest, centre_test_id)
    if not isinstance(offering, CentreTest):
        raise NotFoundError("Offering not found")
    centre = _locked(session, Centre, offering.centre_id)
    test = _locked(session, DiagnosticTest, offering.test_id)
    if not isinstance(centre, Centre) or not isinstance(test, DiagnosticTest):
        raise NotFoundError("Offering not found")
    if not offering.is_active or not centre.is_active or not test.is_active:
        raise ConflictError("Offering is inactive")
    booking = Booking(user_id=user_id, centre_test_id=offering.id, appointment_at=appointment_at, amount_minor=offering.price_minor, currency=offering.currency, status="PENDING")
    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking


def list_bookings(session: Session, user_id: UUID, status: str | None, limit: int, offset: int) -> list[Booking]:
    bookings = [item for item in session.scalars(select(Booking)).all() if isinstance(item, Booking) and item.user_id == user_id]
    if status:
        bookings = [item for item in bookings if item.status == status]
    return sorted(bookings, key=lambda item: (item.created_at, item.id), reverse=True)[offset : offset + limit]


def get_booking(session: Session, user_id: UUID, booking_id: UUID) -> Booking:
    booking = session.get(Booking, booking_id)
    if not isinstance(booking, Booking) or booking.user_id != user_id:
        raise NotFoundError("Booking not found")
    return booking


def booking_context(session: Session, booking: Booking) -> tuple[UUID, UUID]:
    offering = session.get(CentreTest, booking.centre_test_id)
    if not isinstance(offering, CentreTest):
        raise NotFoundError("Booking not found")
    return offering.centre_id, offering.test_id
