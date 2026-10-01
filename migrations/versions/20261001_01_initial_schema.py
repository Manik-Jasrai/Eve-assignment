"""Initial diagnostic booking schema.

Revision ID: 20261001_01
Revises:
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261001_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    ]


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="USER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_timestamps(),
        sa.CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
    )
    op.create_index("uq_users_email_normalized", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "centres",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=300), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_timestamps(),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_centres_name_not_blank"),
        sa.CheckConstraint("length(btrim(location)) > 0", name="ck_centres_location_not_blank"),
    )

    op.create_table(
        "diagnostic_tests",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_timestamps(),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_diagnostic_tests_name_not_blank"),
    )
    op.create_index("uq_diagnostic_tests_name_normalized", "diagnostic_tests", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "centre_tests",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("centre_id", uuid, nullable=False),
        sa.Column("test_id", uuid, nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_timestamps(),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["test_id"], ["diagnostic_tests.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("price_minor > 0", name="ck_centre_tests_price_minor_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_centre_tests_currency_inr"),
    )
    op.create_index("uq_centre_tests_centre_test", "centre_tests", ["centre_id", "test_id"], unique=True)
    op.create_index("ix_centre_tests_test_centre", "centre_tests", ["test_id", "centre_id"])

    op.create_table(
        "bookings",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("centre_test_id", uuid, nullable=False),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["centre_test_id"], ["centre_tests.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount_minor > 0", name="ck_bookings_amount_minor_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_bookings_currency_inr"),
        sa.CheckConstraint("status IN ('PENDING', 'CONFIRMED', 'FAILED', 'CANCELLED')", name="ck_bookings_status"),
    )
    op.create_index("ix_bookings_user_created_id", "bookings", ["user_id", sa.text("created_at DESC"), "id"])
    op.create_index("ix_bookings_centre_test", "bookings", ["centre_test_id"])

    op.create_table(
        "payments",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("booking_id", uuid, nullable=False, unique=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount_minor > 0", name="ck_payments_amount_minor_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_payments_currency_inr"),
        sa.CheckConstraint("status IN ('PENDING', 'SUCCESS', 'FAILED')", name="ck_payments_status"),
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("payment_id", uuid, nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("reported_status", sa.String(length=16), nullable=False),
        sa.Column("disposition", sa.String(length=16), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        *_timestamps(),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("reported_status IN ('SUCCESS', 'FAILED')", name="ck_webhook_events_reported_status"),
        sa.CheckConstraint("disposition IN ('APPLIED', 'NOOP')", name="ck_webhook_events_disposition"),
    )
    op.create_index("uq_webhook_events_provider_event", "webhook_events", ["provider", "event_id"], unique=True)
    op.create_index("ix_webhook_events_payment", "webhook_events", ["payment_id"])


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("centre_tests")
    op.drop_table("diagnostic_tests")
    op.drop_table("centres")
    op.drop_table("users")
