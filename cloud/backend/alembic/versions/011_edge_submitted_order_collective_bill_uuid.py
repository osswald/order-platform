"""Add collective_bill_uuid to edge_submitted_orders for Sammelrechnung queries.

Revision ID: 011_edge_submitted_order_collective_bill_uuid
Revises: 010_edge_submitted_order_reporting_indexes
Create Date: 2026-08-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_edge_submitted_order_collective_bill_uuid"
down_revision: Union[str, Sequence[str], None] = "010_edge_submitted_order_reporting_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_edge_submitted_orders_event_id_collective_bill_uuid"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "edge_submitted_orders" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("edge_submitted_orders")}
    if "collective_bill_uuid" not in columns:
        op.add_column(
            "edge_submitted_orders",
            sa.Column("collective_bill_uuid", sa.String(length=36), nullable=True),
        )

    index_names = {idx["name"] for idx in inspector.get_indexes("edge_submitted_orders")}
    if INDEX_NAME not in index_names:
        op.create_index(
            INDEX_NAME,
            "edge_submitted_orders",
            ["event_id", "collective_bill_uuid"],
        )

    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE edge_submitted_orders
                SET collective_bill_uuid = NULLIF(TRIM(payload->>'collective_bill_uuid'), '')
                WHERE collective_bill_uuid IS NULL
                  AND payload ? 'collective_bill_uuid'
                """
            )
        )
    else:
        # SQLite / other: portable JSON extract where supported; no-op if extract fails.
        try:
            op.execute(
                sa.text(
                    """
                    UPDATE edge_submitted_orders
                    SET collective_bill_uuid = NULLIF(TRIM(json_extract(payload, '$.collective_bill_uuid')), '')
                    WHERE collective_bill_uuid IS NULL
                      AND json_extract(payload, '$.collective_bill_uuid') IS NOT NULL
                    """
                )
            )
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "edge_submitted_orders" not in inspector.get_table_names():
        return

    index_names = {idx["name"] for idx in inspector.get_indexes("edge_submitted_orders")}
    if INDEX_NAME in index_names:
        op.drop_index(INDEX_NAME, table_name="edge_submitted_orders")

    columns = {col["name"] for col in inspector.get_columns("edge_submitted_orders")}
    if "collective_bill_uuid" in columns:
        op.drop_column("edge_submitted_orders", "collective_bill_uuid")
