"""stripe webhook event dedup table

Revision ID: 005_stripe_webhook_events
Revises: 004_merge_cloud_heads
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_stripe_webhook_events"
down_revision: Union[str, Sequence[str], None] = "004_merge_cloud_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id", name="uq_stripe_webhook_events_stripe_event_id"),
    )
    op.create_index("ix_stripe_webhook_events_stripe_event_id", "stripe_webhook_events", ["stripe_event_id"])
    op.create_index("ix_stripe_webhook_events_payment_intent_id", "stripe_webhook_events", ["payment_intent_id"])


def downgrade() -> None:
    op.drop_index("ix_stripe_webhook_events_payment_intent_id", table_name="stripe_webhook_events")
    op.drop_index("ix_stripe_webhook_events_stripe_event_id", table_name="stripe_webhook_events")
    op.drop_table("stripe_webhook_events")
