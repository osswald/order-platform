"""Add device serial/model on sumup_readers for catalog sync and telemetry.

Revision ID: 014_sumup_reader_device_identity
Revises: 013_rental_zubehoer
Create Date: 2026-08-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_sumup_reader_device_identity"
down_revision: Union[str, Sequence[str], None] = "013_rental_zubehoer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "sumup_readers" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("sumup_readers")}
    if "device_identifier" not in columns:
        op.add_column(
            "sumup_readers",
            sa.Column("device_identifier", sa.String(length=128), nullable=True),
        )
    if "device_model" not in columns:
        op.add_column(
            "sumup_readers",
            sa.Column("device_model", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "sumup_readers" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("sumup_readers")}
    if "device_model" in columns:
        op.drop_column("sumup_readers", "device_model")
    if "device_identifier" in columns:
        op.drop_column("sumup_readers", "device_identifier")
