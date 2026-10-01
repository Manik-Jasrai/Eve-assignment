"""Shared payment and booking transition rules with no transaction ownership."""

from app.core.errors import ConflictError
from app.core.states import BookingStatus, PaymentStatus
from app.models.entities import Booking, Payment


def create_pending_payment(booking: Booking) -> Payment:
    """Create a pending payment that copies only server-owned booking values."""
    _validate_money(booking.amount_minor, booking.currency)
    return Payment(
        booking_id=booking.id,
        amount_minor=booking.amount_minor,
        currency=booking.currency,
        status=PaymentStatus.PENDING,
    )


def apply_payment_result(payment: Payment, booking: Booking, result: PaymentStatus | str) -> bool:
    """Apply a terminal result and return whether it changed persisted state."""
    target = _terminal_result(result)
    _validate_links(payment, booking)
    _validate_money(payment.amount_minor, payment.currency)
    _validate_money(booking.amount_minor, booking.currency)
    if payment.amount_minor != booking.amount_minor or payment.currency != booking.currency:
        raise ConflictError("Payment does not match booking amount or currency")

    payment_status = PaymentStatus(payment.status)
    booking_status = BookingStatus(booking.status)
    if booking_status is BookingStatus.CANCELLED:
        raise ConflictError("Cancelled bookings cannot be paid")

    expected_booking_status = BookingStatus.CONFIRMED if target is PaymentStatus.SUCCESS else BookingStatus.FAILED
    if payment_status is PaymentStatus.PENDING:
        if booking_status is not BookingStatus.PENDING:
            raise ConflictError("Payment and booking states are inconsistent")
        payment.status = target
        booking.status = expected_booking_status
        return True

    if payment_status is not target or booking_status is not expected_booking_status:
        raise ConflictError("Payment and booking states are inconsistent")
    return False


def _terminal_result(result: PaymentStatus | str) -> PaymentStatus:
    try:
        status = PaymentStatus(result)
    except ValueError as exc:
        raise ConflictError("Payment result must be SUCCESS or FAILED") from exc
    if status is PaymentStatus.PENDING:
        raise ConflictError("Payment result must be SUCCESS or FAILED")
    return status


def _validate_money(amount_minor: int, currency: str) -> None:
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0 or currency != "INR":
        raise ConflictError("Payment amount and currency are invalid")


def _validate_links(payment: Payment, booking: Booking) -> None:
    if payment.booking_id != booking.id:
        raise ConflictError("Payment does not belong to booking")
