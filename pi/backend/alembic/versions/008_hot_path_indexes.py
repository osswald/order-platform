"""Add hot-path SQLite indexes for print queue, open orders, outbox, kitchen."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_hot_path_indexes"
down_revision: str | None = "007_synced_bundle_etag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_print_jobs_status", "print_jobs", ["status"], unique=False)
    op.create_index(
        "ix_order_submissions_event_payment",
        "order_submissions",
        ["event_id", "payment_status"],
        unique=False,
    )
    op.create_index("ix_sync_outbox_status", "sync_outbox", ["status"], unique=False)
    op.create_index(
        "ix_kitchen_tickets_event_status",
        "kitchen_tickets",
        ["event_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kitchen_tickets_event_status", table_name="kitchen_tickets")
    op.drop_index("ix_sync_outbox_status", table_name="sync_outbox")
    op.drop_index("ix_order_submissions_event_payment", table_name="order_submissions")
    op.drop_index("ix_print_jobs_status", table_name="print_jobs")
