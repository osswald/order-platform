"""edge operational snapshots for Pi restore

Revision ID: 003_edge_snapshots
Revises: 002_edge_cash
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_edge_snapshots"
down_revision: Union[str, None] = "002_edge_cash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "edge_order_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("appliance_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("logical_client_order_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["appliance_id"], ["appliances.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.UniqueConstraint(
            "organisation_id",
            "event_id",
            "logical_client_order_id",
            name="uq_edge_order_snapshot_logical",
        ),
    )
    op.create_index("ix_edge_order_snapshots_org_event", "edge_order_snapshots", ["organisation_id", "event_id"])

    op.create_table(
        "edge_kitchen_ticket_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("appliance_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("logical_client_order_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["appliance_id"], ["appliances.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.UniqueConstraint(
            "organisation_id",
            "event_id",
            "logical_client_order_id",
            name="uq_edge_kitchen_snapshot_logical",
        ),
    )
    op.create_index(
        "ix_edge_kitchen_ticket_snapshots_org_event",
        "edge_kitchen_ticket_snapshots",
        ["organisation_id", "event_id"],
    )

    op.add_column("edge_cash_sessions", sa.Column("subject_key", sa.String(length=128), nullable=True))
    op.create_index("ix_edge_cash_sessions_subject_key", "edge_cash_sessions", ["subject_key"])
    op.create_index(
        "ix_edge_cash_sessions_org_event_subject",
        "edge_cash_sessions",
        ["organisation_id", "event_id", "subject_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_edge_cash_sessions_org_event_subject", table_name="edge_cash_sessions")
    op.drop_index("ix_edge_cash_sessions_subject_key", table_name="edge_cash_sessions")
    op.drop_column("edge_cash_sessions", "subject_key")
    op.drop_index("ix_edge_kitchen_ticket_snapshots_org_event", table_name="edge_kitchen_ticket_snapshots")
    op.drop_table("edge_kitchen_ticket_snapshots")
    op.drop_index("ix_edge_order_snapshots_org_event", table_name="edge_order_snapshots")
    op.drop_table("edge_order_snapshots")
