"""Use webhook business payloads for idempotency.

Revision ID: 20261003_01
Revises: 20261001_01
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20261003_01"
down_revision: str | None = "20261001_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("uq_webhook_events_provider_event", table_name="webhook_events")
    op.create_index(
        "ix_webhook_events_provider_event",
        "webhook_events",
        ["provider", "event_id"],
        unique=False,
    )
    op.execute(
        """
        DELETE FROM webhook_events AS duplicate
        USING webhook_events AS retained
        WHERE duplicate.provider = retained.provider
          AND duplicate.payment_id = retained.payment_id
          AND duplicate.reported_status = retained.reported_status
          AND (duplicate.received_at, duplicate.id) > (retained.received_at, retained.id)
        """
    )
    op.create_index(
        "uq_webhook_events_business_payload",
        "webhook_events",
        ["provider", "payment_id", "reported_status"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_webhook_events_business_payload", table_name="webhook_events")
    op.drop_index("ix_webhook_events_provider_event", table_name="webhook_events")
    op.execute(
        """
        DELETE FROM webhook_events AS duplicate
        USING webhook_events AS retained
        WHERE duplicate.provider = retained.provider
          AND duplicate.event_id = retained.event_id
          AND (duplicate.received_at, duplicate.id) > (retained.received_at, retained.id)
        """
    )
    op.create_index(
        "uq_webhook_events_provider_event",
        "webhook_events",
        ["provider", "event_id"],
        unique=True,
    )
