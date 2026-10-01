"""Unit coverage for payment state transitions."""

from uuid import uuid4

import pytest

from app.core.errors import ConflictError
from app.core.states import BookingStatus, PaymentStatus
from app.integrations.simulated_provider import simulate_result
from app.models.entities import Booking
from app.services.payment_state import apply_payment_result, create_pending_payment


def _booking(status: BookingStatus = BookingStatus.PENDING) -> Booking:
    return Booking(
        id=uuid4(), user_id=uuid4(), centre_test_id=uuid4(), appointment_at="2030-01-01T10:00:00+00:00",
        amount_minor=49900, currency="INR", status=status,
    )


@pytest.mark.parametrize(
    ("result", "booking_status"),
    [(PaymentStatus.SUCCESS, BookingStatus.CONFIRMED), (PaymentStatus.FAILED, BookingStatus.FAILED)],
)
def test_pending_payment_transitions(result: PaymentStatus, booking_status: BookingStatus) -> None:
    booking = _booking()
    payment = create_pending_payment(booking)

    assert apply_payment_result(payment, booking, result) is True
    assert payment.status == result
    assert booking.status == booking_status
    assert apply_payment_result(payment, booking, result) is False


def test_contradictory_and_cancelled_results_are_rejected() -> None:
    booking = _booking()
    payment = create_pending_payment(booking)
    apply_payment_result(payment, booking, PaymentStatus.SUCCESS)
    with pytest.raises(ConflictError):
        apply_payment_result(payment, booking, PaymentStatus.FAILED)

    cancelled = _booking(BookingStatus.CANCELLED)
    with pytest.raises(ConflictError):
        apply_payment_result(create_pending_payment(cancelled), cancelled, PaymentStatus.SUCCESS)


def test_invalid_payment_records_are_rejected() -> None:
    booking = _booking()
    payment = create_pending_payment(booking)
    payment.amount_minor = 1
    with pytest.raises(ConflictError):
        apply_payment_result(payment, booking, PaymentStatus.SUCCESS)


def test_simulator_is_deterministic_and_rejects_pending() -> None:
    assert simulate_result("SUCCESS") is PaymentStatus.SUCCESS
    assert simulate_result(PaymentStatus.FAILED) is PaymentStatus.FAILED
    with pytest.raises(Exception):
        simulate_result("PENDING")
