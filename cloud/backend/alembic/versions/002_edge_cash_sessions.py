"""edge cash sessions mirror

Revision ID: 002_edge_cash
Revises: 001_edge_ops
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_edge_cash"
down_revision: Union[str, None] = "001_edge_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "edge_cash_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("appliance_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("cash_session_id", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("cash_register_uuid", sa.String(length=36), nullable=True),
        sa.Column("subject_name", sa.String(length=128), nullable=False),
        sa.Column("operator_waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("opening_balance_cents", sa.Integer(), nullable=False),
        sa.Column("wallet_cents", sa.Integer(), nullable=False),
        sa.Column("total_cash_cents", sa.Integer(), nullable=False),
        sa.Column("total_non_cash_cents", sa.Integer(), nullable=False),
        sa.Column("counted_cash_cents", sa.Integer(), nullable=True),
        sa.Column("variance_cents", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index(
        "ix_edge_cash_sessions_lookup",
        "edge_cash_sessions",
        ["appliance_id", "event_id", "cash_session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_edge_cash_sessions_lookup", table_name="edge_cash_sessions")
    op.drop_table("edge_cash_sessions")
