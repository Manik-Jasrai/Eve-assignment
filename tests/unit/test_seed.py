"""Tests for the coherent development seed dataset."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from app.models.entities import Booking, Centre, CentreTest, DiagnosticTest, Payment, User, WebhookEvent
from scripts.seed import SeedSummary, seed_database


def _records_by_type(summary: SeedSummary) -> dict[type[object], tuple[object, ...]]:
    return {
        User: summary.users,
        Centre: summary.centres,
        DiagnosticTest: summary.tests,
        CentreTest: summary.offerings,
        Booking: summary.bookings,
        Payment: summary.payments,
        WebhookEvent: summary.webhook_events,
    }


def test_seed_database_builds_three_correlated_rows_per_table_and_is_repeatable() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    session.scalar.return_value = None
    seeded_at = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)

    with patch("scripts.seed._password_hash.hash", return_value="hashed-password"):
        summary = seed_database(session, "Admin@Example.com", "development-password", seeded_at)

    records_by_type = _records_by_type(summary)
    assert all(len(records) == 3 for records in records_by_type.values())
    assert summary.users[0].email == "admin@example.com"
    assert {booking.user_id for booking in summary.bookings} <= {user.id for user in summary.users}
    assert {booking.centre_test_id for booking in summary.bookings} == {
        offering.id for offering in summary.offerings
    }
    assert {payment.booking_id for payment in summary.payments} == {booking.id for booking in summary.bookings}
    assert {event.payment_id for event in summary.webhook_events} == {payment.id for payment in summary.payments}
    assert [booking.status for booking in summary.bookings] == ["CONFIRMED", "FAILED", "CONFIRMED"]
    assert [payment.status for payment in summary.payments] == ["SUCCESS", "FAILED", "SUCCESS"]
    assert session.add.call_count == 21
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

    persisted = {
        (model, record.id): record
        for model, records in records_by_type.items()
        for record in records
    }
    rerun_session = Mock(spec=Session)
    rerun_session.get.side_effect = lambda model, record_id: persisted.get((model, record_id))

    with patch("scripts.seed._password_hash.hash", return_value="new-hash"):
        rerun_summary = seed_database(
            rerun_session,
            "admin@example.com",
            "development-password",
            seeded_at,
        )

    assert rerun_summary == summary
    rerun_session.add.assert_not_called()
    rerun_session.scalar.assert_not_called()
    rerun_session.commit.assert_called_once_with()
    rerun_session.rollback.assert_not_called()
