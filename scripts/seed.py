"""Seed a small, coherent dataset across every application table."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.states import BookingStatus, PaymentStatus
from app.db.session import get_session_factory
from app.models.entities import (
    Booking,
    Centre,
    CentreTest,
    DiagnosticTest,
    Payment,
    TimestampedEntity,
    User,
    WebhookEvent,
)
from app.services.auth import _password_hash
from app.services.payments import payload_hash


@dataclass(frozen=True)
class SeedSummary:
    """Records created or refreshed by one seed run."""

    users: tuple[User, ...]
    centres: tuple[Centre, ...]
    tests: tuple[DiagnosticTest, ...]
    offerings: tuple[CentreTest, ...]
    bookings: tuple[Booking, ...]
    payments: tuple[Payment, ...]
    webhook_events: tuple[WebhookEvent, ...]


EntityT = TypeVar("EntityT", bound=TimestampedEntity)


def _seed_id(key: str) -> UUID:
    """Return a stable ID so the seed can be run repeatedly without duplicates."""
    return uuid5(NAMESPACE_URL, f"https://eve.local/seed/{key}")


def _find_seed_record(
    session: Session,
    model: type[EntityT],
    key: str,
    natural_key_query: Select[tuple[EntityT]],
) -> EntityT | None:
    record = session.get(model, _seed_id(key))
    if record is not None:
        return record
    return session.scalar(natural_key_query)


def _seed_users(session: Session, admin_email: str, password_hash: str) -> tuple[User, ...]:
    definitions: tuple[tuple[str, str, str], ...] = (
        ("users/admin", admin_email, "ADMIN"),
        ("users/patient-one", "patient.one@example.com", "USER"),
        ("users/patient-two", "patient.two@example.com", "USER"),
    )
    if len({email for _, email, _ in definitions}) != len(definitions):
        raise ValueError("SEED_ADMIN_EMAIL must differ from the seeded patient emails")

    records: list[User] = []
    for key, email, role in definitions:
        user = _find_seed_record(
            session,
            User,
            key,
            select(User).where(func.lower(User.email) == email),
        )
        if user is None:
            user = User(id=_seed_id(key), email=email, password_hash=password_hash, role=role, is_active=True)
            session.add(user)
        else:
            user.email = email
            user.role = role
            user.is_active = True
        records.append(user)
    return tuple(records)


def _seed_centres(session: Session) -> tuple[Centre, ...]:
    definitions: tuple[tuple[str, str, str], ...] = (
        ("centres/delhi", "EVE Diagnostic Centre", "Delhi"),
        ("centres/gurugram", "EVE Health Hub", "Gurugram"),
        ("centres/noida", "EVE Pathology Lab", "Noida"),
    )
    records: list[Centre] = []
    for key, name, location in definitions:
        centre = _find_seed_record(session, Centre, key, select(Centre).where(Centre.name == name))
        if centre is None:
            centre = Centre(id=_seed_id(key), name=name, location=location, is_active=True)
            session.add(centre)
        else:
            centre.name = name
            centre.location = location
            centre.is_active = True
        records.append(centre)
    return tuple(records)


def _seed_tests(session: Session) -> tuple[DiagnosticTest, ...]:
    definitions: tuple[tuple[str, str, str], ...] = (
        ("tests/cbc", "Complete Blood Count", "Measures red cells, white cells, platelets, and haemoglobin."),
        ("tests/thyroid", "Thyroid Profile", "Measures T3, T4, and thyroid-stimulating hormone levels."),
        ("tests/hba1c", "HbA1c", "Estimates average blood glucose over the previous two to three months."),
    )
    records: list[DiagnosticTest] = []
    for key, name, description in definitions:
        test = _find_seed_record(
            session,
            DiagnosticTest,
            key,
            select(DiagnosticTest).where(func.lower(DiagnosticTest.name) == name.lower()),
        )
        if test is None:
            test = DiagnosticTest(id=_seed_id(key), name=name, description=description, is_active=True)
            session.add(test)
        else:
            test.name = name
            test.description = description
            test.is_active = True
        records.append(test)
    return tuple(records)


def _seed_offerings(
    session: Session,
    centres: tuple[Centre, ...],
    tests: tuple[DiagnosticTest, ...],
) -> tuple[CentreTest, ...]:
    definitions: tuple[tuple[str, int, int, int], ...] = (
        ("offerings/delhi-cbc", 0, 0, 49_900),
        ("offerings/gurugram-thyroid", 1, 1, 79_900),
        ("offerings/noida-hba1c", 2, 2, 59_900),
    )
    records: list[CentreTest] = []
    for key, centre_index, test_index, price_minor in definitions:
        centre = centres[centre_index]
        test = tests[test_index]
        offering = _find_seed_record(
            session,
            CentreTest,
            key,
            select(CentreTest).where(CentreTest.centre_id == centre.id, CentreTest.test_id == test.id),
        )
        if offering is None:
            offering = CentreTest(
                id=_seed_id(key),
                centre_id=centre.id,
                test_id=test.id,
                price_minor=price_minor,
                currency="INR",
                is_active=True,
            )
            session.add(offering)
        else:
            offering.centre_id = centre.id
            offering.test_id = test.id
            offering.price_minor = price_minor
            offering.currency = "INR"
            offering.is_active = True
        records.append(offering)
    return tuple(records)


def _seed_bookings(
    session: Session,
    users: tuple[User, ...],
    offerings: tuple[CentreTest, ...],
    now: datetime,
) -> tuple[Booking, ...]:
    definitions: tuple[tuple[str, int, int, int, BookingStatus], ...] = (
        ("bookings/patient-one-cbc", 1, 0, 7, BookingStatus.CONFIRMED),
        ("bookings/patient-two-thyroid", 2, 1, 14, BookingStatus.FAILED),
        ("bookings/patient-one-hba1c", 1, 2, 21, BookingStatus.CONFIRMED),
    )
    records: list[Booking] = []
    for key, user_index, offering_index, days_ahead, status in definitions:
        user = users[user_index]
        offering = offerings[offering_index]
        booking = _find_seed_record(
            session,
            Booking,
            key,
            select(Booking).where(Booking.id == _seed_id(key)),
        )
        appointment_at = now + timedelta(days=days_ahead)
        if booking is None:
            booking = Booking(
                id=_seed_id(key),
                user_id=user.id,
                centre_test_id=offering.id,
                appointment_at=appointment_at,
                amount_minor=offering.price_minor,
                currency=offering.currency,
                status=status.value,
            )
            session.add(booking)
        else:
            booking.user_id = user.id
            booking.centre_test_id = offering.id
            booking.appointment_at = appointment_at
            booking.amount_minor = offering.price_minor
            booking.currency = offering.currency
            booking.status = status.value
        records.append(booking)
    return tuple(records)


def _seed_payments(session: Session, bookings: tuple[Booking, ...]) -> tuple[Payment, ...]:
    statuses: tuple[PaymentStatus, ...] = (
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.SUCCESS,
    )
    records: list[Payment] = []
    for index, (booking, status) in enumerate(zip(bookings, statuses, strict=True), start=1):
        key = f"payments/payment-{index}"
        payment = _find_seed_record(
            session,
            Payment,
            key,
            select(Payment).where(Payment.booking_id == booking.id),
        )
        if payment is None:
            payment = Payment(
                id=_seed_id(key),
                booking_id=booking.id,
                amount_minor=booking.amount_minor,
                currency=booking.currency,
                status=status.value,
            )
            session.add(payment)
        else:
            payment.booking_id = booking.id
            payment.amount_minor = booking.amount_minor
            payment.currency = booking.currency
            payment.status = status.value
        records.append(payment)
    return tuple(records)


def _seed_webhook_events(session: Session, payments: tuple[Payment, ...]) -> tuple[WebhookEvent, ...]:
    definitions: tuple[tuple[str, PaymentStatus, str], ...] = (
        ("evt-seed-payment-001", PaymentStatus.SUCCESS, "APPLIED"),
        ("evt-seed-payment-002", PaymentStatus.FAILED, "APPLIED"),
        ("evt-seed-payment-003", PaymentStatus.SUCCESS, "NOOP"),
    )
    records: list[WebhookEvent] = []
    for index, (payment, definition) in enumerate(zip(payments, definitions, strict=True), start=1):
        event_id, reported_status, disposition = definition
        key = f"webhook-events/event-{index}"
        digest = payload_hash(
            payment.id,
            reported_status,
            payment.amount_minor,
            payment.currency,
        )
        event = _find_seed_record(
            session,
            WebhookEvent,
            key,
            select(WebhookEvent).where(
                WebhookEvent.provider == "mock",
                WebhookEvent.event_id == event_id,
            ),
        )
        if event is None:
            event = WebhookEvent(
                id=_seed_id(key),
                provider="mock",
                event_id=event_id,
                payment_id=payment.id,
                payload_hash=digest,
                reported_status=reported_status.value,
                disposition=disposition,
            )
            session.add(event)
        else:
            event.payment_id = payment.id
            event.payload_hash = digest
            event.reported_status = reported_status.value
            event.disposition = disposition
        records.append(event)
    return tuple(records)


def seed_database(
    session: Session,
    admin_email: str,
    admin_password: str,
    now: datetime | None = None,
) -> SeedSummary:
    """Create or refresh the development seed dataset in one transaction."""
    normalized_admin_email = admin_email.strip().lower()
    effective_now = now or datetime.now(UTC)
    if effective_now.tzinfo is None or effective_now.utcoffset() is None:
        raise ValueError("Seed time must be timezone-aware")

    shared_password_hash = _password_hash.hash(admin_password)
    try:
        users = _seed_users(session, normalized_admin_email, shared_password_hash)
        centres = _seed_centres(session)
        tests = _seed_tests(session)
        session.flush()
        offerings = _seed_offerings(session, centres, tests)
        session.flush()
        bookings = _seed_bookings(session, users, offerings, effective_now)
        session.flush()
        payments = _seed_payments(session, bookings)
        session.flush()
        webhook_events = _seed_webhook_events(session, payments)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return SeedSummary(users, centres, tests, offerings, bookings, payments, webhook_events)


def _print_summary(summary: SeedSummary) -> None:
    groups: tuple[tuple[str, tuple[TimestampedEntity, ...]], ...] = (
        ("user", summary.users),
        ("centre", summary.centres),
        ("test", summary.tests),
        ("offering", summary.offerings),
        ("booking", summary.bookings),
        ("payment", summary.payments),
        ("webhook_event", summary.webhook_events),
    )
    for label, records in groups:
        print(f"{label}_ids={','.join(str(record.id) for record in records)}")


def main() -> None:
    settings = get_settings()
    session = get_session_factory()()
    try:
        summary = seed_database(
            session,
            settings.seed_admin_email,
            settings.seed_admin_password.get_secret_value(),
        )
        _print_summary(summary)
    finally:
        session.close()


if __name__ == "__main__":
    main()
