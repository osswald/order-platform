"""cash shift sessions — waiter/register subjects + ledger

Revision ID: 002_shift_sessions
Revises: 001_v3_ops
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_shift_sessions"
down_revision: Union[str, None] = "001_v3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cash_sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("subject_type", sa.String(length=32), nullable=False, server_default="cash_register")
        )
        batch_op.add_column(sa.Column("waiter_uuid", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column("subject_name", sa.String(length=128), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("wallet_cents", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("total_non_cash_cents", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.alter_column("cash_register_uuid", existing_type=sa.String(length=36), nullable=True)

    op.create_table(
        "cash_session_ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cash_session_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affects_wallet", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("voucher_definition_uuid", sa.String(length=36), nullable=True),
        sa.Column("voucher_name", sa.String(length=128), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_session_ledger_session", "cash_session_ledger", ["cash_session_id"])


def downgrade() -> None:
    op.drop_index("ix_cash_session_ledger_session", table_name="cash_session_ledger")
    op.drop_table("cash_session_ledger")
    with op.batch_alter_table("cash_sessions", schema=None) as batch_op:
        batch_op.drop_column("total_non_cash_cents")
        batch_op.drop_column("wallet_cents")
        batch_op.drop_column("subject_name")
        batch_op.drop_column("waiter_uuid")
        batch_op.drop_column("subject_type")
        batch_op.alter_column("cash_register_uuid", existing_type=sa.String(length=36), nullable=False)
