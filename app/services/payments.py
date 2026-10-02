"""Payment initiation and idempotent webhook finalization workflows."""

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.states import BookingStatus, PaymentStatus, TerminalPaymentStatus, WebhookDisposition
from app.models.entities import Booking, Payment, WebhookEvent
from app.services.payment_state import apply_payment_result, create_pending_payment


def _all(session: Session, model: type[object]) -> list[object]:
    return list(session.scalars(select(model)).all())


def _commit(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def _payment_for_booking(session: Session, booking_id: UUID) -> Payment | None:
    return next(
        (payment for payment in _all(session, Payment) if isinstance(payment, Payment) and payment.booking_id == booking_id),
        None,
    )


def _locked(session: Session, model: type[object], record_id: UUID) -> object | None:
    """Return one record under a row lock, or use the test double's compatible API."""
    if hasattr(session, "lock"):
        return session.lock(model, record_id)  # type: ignore[attr-defined]
    return session.execute(  # type: ignore[attr-defined]
        select(model).where(model.id == record_id).with_for_update()
    ).scalar_one_or_none()


def create_payment(session: Session, user_id: UUID, booking_id: UUID) -> tuple[Payment, bool]:
    booking = _locked(session, Booking, booking_id)
    if not isinstance(booking, Booking) or booking.user_id != user_id:
        raise NotFoundError("Booking not found")
    payment = _payment_for_booking(session, booking_id)
    if payment is not None:
        payment = _locked(session, Payment, payment.id)
        if not isinstance(payment, Payment):
            raise NotFoundError("Payment not found")
        return payment, False
    if BookingStatus(booking.status) is not BookingStatus.PENDING:
        raise ConflictError("Only pending bookings can start payment")
    payment = create_pending_payment(booking)
    session.add(payment)
    _commit(session)
    session.refresh(payment)
    return payment, True


def get_payment(session: Session, user_id: UUID, payment_id: UUID) -> Payment:
    payment = session.get(Payment, payment_id)
    if not isinstance(payment, Payment):
        raise NotFoundError("Payment not found")
    booking = session.get(Booking, payment.booking_id)
    if not isinstance(booking, Booking) or booking.user_id != user_id:
        raise NotFoundError("Payment not found")
    return payment


def payload_hash(payment_id: UUID, status: PaymentStatus, amount_minor: int, currency: str) -> str:
    raw = json.dumps(
        {
            "amount_minor": amount_minor,
            "currency": currency,
            "payment_id": str(payment_id),
            "status": status,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def handle_webhook(
    session: Session,
    event_id: str,
    payment_id: UUID,
    result: TerminalPaymentStatus,
    amount_minor: int,
    currency: str,
) -> WebhookDisposition:
    payment = session.get(Payment, payment_id)
    if not isinstance(payment, Payment):
        raise NotFoundError("Payment not found")
    booking = _locked(session, Booking, payment.booking_id)
    if not isinstance(booking, Booking):
        raise NotFoundError("Payment not found")
    payment = _locked(session, Payment, payment_id)
    if not isinstance(payment, Payment) or payment.booking_id != booking.id:
        raise NotFoundError("Payment not found")
    if amount_minor != payment.amount_minor or currency != payment.currency:
        raise BusinessRuleError("Webhook amount or currency does not match payment")
    old = next(
        (
            event
            for event in _all(session, WebhookEvent)
            if isinstance(event, WebhookEvent)
            and event.provider == "mock"
            and event.payment_id == payment_id
            and PaymentStatus(event.reported_status) is result
        ),
        None,
    )
    if old is not None:
        return WebhookDisposition.DUPLICATE
    changed = apply_payment_result(payment, booking, result)
    disposition = WebhookDisposition.APPLIED if changed else WebhookDisposition.NOOP
    event = WebhookEvent(
        provider="mock",
        event_id=event_id,
        payment_id=payment.id,
        payload_hash=payload_hash(payment.id, result, amount_minor, currency),
        reported_status=result,
        disposition=disposition,
    )
    session.add(event)
    _commit(session)
    return disposition
