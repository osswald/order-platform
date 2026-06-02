"""remove legacy appliance edge credentials

Revision ID: 002_remove_legacy_appliance_edge_credentials
Revises: 001_edge_ops
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_remove_legacy_appliance_edge_credentials"
down_revision: Union[str, None] = "001_edge_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("appliances") as batch_op:
        batch_op.drop_column("edge_secret_hash")
        batch_op.drop_column("edge_client_id")


def downgrade() -> None:
    with op.batch_alter_table("appliances") as batch_op:
        batch_op.add_column(sa.Column("edge_client_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("edge_secret_hash", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_appliances_edge_client_id"), "appliances", ["edge_client_id"], unique=True)
