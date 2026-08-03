"""cash_session_uuid for durable multi-shift identity

Revision ID: 006_cash_session_uuid
Revises: 005_station_pickups
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_cash_session_uuid"
down_revision: Union[str, None] = "005_station_pickups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cash_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cash_session_uuid", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_cash_sessions_cash_session_uuid", ["cash_session_uuid"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("cash_sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_cash_sessions_cash_session_uuid")
        batch_op.drop_column("cash_session_uuid")
