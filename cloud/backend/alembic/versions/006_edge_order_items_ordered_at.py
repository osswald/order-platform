"""edge_order_items ordered_at for stats timeframe filtering

Revision ID: 006_edge_order_items_ordered_at
Revises: 005_stripe_webhook_events
Create Date: 2026-06-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_edge_order_items_ordered_at"
down_revision: Union[str, Sequence[str], None] = "005_stripe_webhook_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("edge_order_items")}
    if "ordered_at" not in cols:
        op.add_column("edge_order_items", sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True))

    index_names = {idx["name"] for idx in inspector.get_indexes("edge_order_items")}
    if "ix_edge_order_items_event_id_ordered_at" not in index_names:
        op.create_index(
            "ix_edge_order_items_event_id_ordered_at",
            "edge_order_items",
            ["event_id", "ordered_at"],
        )

    op.execute("UPDATE edge_order_items SET ordered_at = created_at WHERE ordered_at IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {idx["name"] for idx in inspector.get_indexes("edge_order_items")}
    if "ix_edge_order_items_event_id_ordered_at" in index_names:
        op.drop_index("ix_edge_order_items_event_id_ordered_at", table_name="edge_order_items")
    cols = {c["name"] for c in inspector.get_columns("edge_order_items")}
    if "ordered_at" in cols:
        op.drop_column("edge_order_items", "ordered_at")
