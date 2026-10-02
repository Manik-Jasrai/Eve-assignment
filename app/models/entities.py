"""Core persistence entities for the diagnostic booking workflow."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, desc, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampedEntity(Base):
    """Abstract base with UUID identifiers and database-managed creation time."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampedEntity):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ADMIN')", name="role"),
        Index("uq_users_email_normalized", text("lower(email)"), unique=True),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="USER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Centre(TimestampedEntity):
    __tablename__ = "centres"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint("length(btrim(location)) > 0", name="location_not_blank"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class DiagnosticTest(TimestampedEntity):
    __tablename__ = "diagnostic_tests"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        Index("uq_diagnostic_tests_name_normalized", text("lower(name)"), unique=True),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class CentreTest(TimestampedEntity):
    __tablename__ = "centre_tests"
    __table_args__ = (
        CheckConstraint("price_minor > 0", name="price_minor_positive"),
        CheckConstraint("currency = 'INR'", name="currency_inr"),
        Index("uq_centre_tests_centre_test", "centre_id", "test_id", unique=True),
        Index("ix_centre_tests_test_centre", "test_id", "centre_id"),
    )

    centre_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centres.id", ondelete="RESTRICT"), nullable=False
    )
    test_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), nullable=False
    )
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Booking(TimestampedEntity):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        CheckConstraint("currency = 'INR'", name="currency_inr"),
        CheckConstraint("status IN ('PENDING', 'CONFIRMED', 'FAILED', 'CANCELLED')", name="status"),
        Index("ix_bookings_user_created_id", "user_id", desc("created_at"), "id"),
        Index("ix_bookings_centre_test", "centre_test_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    centre_test_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centre_tests.id", ondelete="RESTRICT"), nullable=False
    )
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")


class Payment(TimestampedEntity):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        CheckConstraint("currency = 'INR'", name="currency_inr"),
        CheckConstraint("status IN ('PENDING', 'SUCCESS', 'FAILED')", name="status"),
    )

    booking_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")


class WebhookEvent(TimestampedEntity):
    __tablename__ = "webhook_events"
    __table_args__ = (
        CheckConstraint("reported_status IN ('SUCCESS', 'FAILED')", name="reported_status"),
        CheckConstraint("disposition IN ('APPLIED', 'NOOP')", name="disposition"),
        Index("ix_webhook_events_provider_event", "provider", "event_id"),
        Index(
            "uq_webhook_events_business_payload",
            "provider",
            "payment_id",
            "reported_status",
            unique=True,
        ),
        Index("ix_webhook_events_payment", "payment_id"),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reported_status: Mapped[str] = mapped_column(String(16), nullable=False)
    disposition: Mapped[str] = mapped_column(String(16), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
