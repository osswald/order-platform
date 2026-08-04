"""Add local_stock_state overlay for monitored article/ingredient stock."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_local_stock_overlay"
down_revision: str | None = "008_hot_path_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "local_stock_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("entity_kind", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("in_stock", sa.Float(), nullable=False),
        sa.Column("monitor_stock", sa.Boolean(), nullable=False),
        sa.Column("sellable", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "entity_kind",
            "entity_id",
            name="uq_local_stock_state_event_kind_id",
        ),
    )
    op.create_index("ix_local_stock_state_event_id", "local_stock_state", ["event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_local_stock_state_event_id", table_name="local_stock_state")
    op.drop_table("local_stock_state")
