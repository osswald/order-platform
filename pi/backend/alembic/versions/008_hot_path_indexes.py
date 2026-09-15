"""Add hot-path SQLite indexes for print queue, open orders, outbox, kitchen."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_hot_path_indexes"
down_revision: str | None = "007_synced_bundle_etag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return index_name in {ix["name"] for ix in inspector.get_indexes(table)}


def upgrade() -> None:
    if not _has_index("print_jobs", "ix_print_jobs_status"):
        op.create_index("ix_print_jobs_status", "print_jobs", ["status"], unique=False)
    if not _has_index("order_submissions", "ix_order_submissions_event_payment"):
        op.create_index(
            "ix_order_submissions_event_payment",
            "order_submissions",
            ["event_id", "payment_status"],
            unique=False,
        )
    if not _has_index("sync_outbox", "ix_sync_outbox_status"):
        op.create_index("ix_sync_outbox_status", "sync_outbox", ["status"], unique=False)
    if not _has_index("kitchen_tickets", "ix_kitchen_tickets_event_status"):
        op.create_index(
            "ix_kitchen_tickets_event_status",
            "kitchen_tickets",
            ["event_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("kitchen_tickets", "ix_kitchen_tickets_event_status"):
        op.drop_index("ix_kitchen_tickets_event_status", table_name="kitchen_tickets")
    if _has_index("sync_outbox", "ix_sync_outbox_status"):
        op.drop_index("ix_sync_outbox_status", table_name="sync_outbox")
    if _has_index("order_submissions", "ix_order_submissions_event_payment"):
        op.drop_index("ix_order_submissions_event_payment", table_name="order_submissions")
    if _has_index("print_jobs", "ix_print_jobs_status"):
        op.drop_index("ix_print_jobs_status", table_name="print_jobs")
