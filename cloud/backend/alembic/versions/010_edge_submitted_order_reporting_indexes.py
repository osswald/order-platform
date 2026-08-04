"""Add reporting indexes to edge_submitted_orders

Adds indexes on (event_id) and (organisation_id) for EdgeSubmittedOrder
so busy-event reporting queries do not require full table scans.

Revision ID: 010_edge_submitted_order_reporting_indexes
Revises: 009_cash_session_uuid
Create Date: 2026-08-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_edge_submitted_order_reporting_indexes"
down_revision: Union[str, Sequence[str], None] = "009_cash_session_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Guard: if the table was dropped and will be recreated by create_all, skip here.
    if "edge_submitted_orders" not in inspector.get_table_names():
        return

    index_names = {idx["name"] for idx in inspector.get_indexes("edge_submitted_orders")}

    if "ix_edge_submitted_orders_event_id" not in index_names:
        op.create_index(
            "ix_edge_submitted_orders_event_id",
            "edge_submitted_orders",
            ["event_id"],
        )

    if "ix_edge_submitted_orders_organisation_id" not in index_names:
        op.create_index(
            "ix_edge_submitted_orders_organisation_id",
            "edge_submitted_orders",
            ["organisation_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {idx["name"] for idx in inspector.get_indexes("edge_submitted_orders")}

    if "ix_edge_submitted_orders_event_id" in index_names:
        op.drop_index("ix_edge_submitted_orders_event_id", table_name="edge_submitted_orders")

    if "ix_edge_submitted_orders_organisation_id" in index_names:
        op.drop_index("ix_edge_submitted_orders_organisation_id", table_name="edge_submitted_orders")
