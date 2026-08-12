"""Add rental Zubehör catalog and rental lines tables.

Revision ID: 013_rental_zubehoer
Revises: 012_rentals_and_lending_rental_id
Create Date: 2026-08-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_rental_zubehoer"
down_revision: Union[str, Sequence[str], None] = "012_rentals_and_lending_rental_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "rental_zubehoer_catalog" not in tables:
        op.create_table(
            "rental_zubehoer_catalog",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("hire_company_id", sa.Integer(), sa.ForeignKey("hire_companies.id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("default_quantity", sa.Integer(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_rental_zubehoer_catalog_id", "rental_zubehoer_catalog", ["id"])
        op.create_index(
            "ix_rental_zubehoer_catalog_hire_company_id",
            "rental_zubehoer_catalog",
            ["hire_company_id"],
        )

    if "rental_zubehoer_lines" not in tables:
        op.create_table(
            "rental_zubehoer_lines",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rental_id", sa.Integer(), sa.ForeignKey("rentals.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "catalog_item_id",
                sa.Integer(),
                sa.ForeignKey("rental_zubehoer_catalog.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_rental_zubehoer_lines_id", "rental_zubehoer_lines", ["id"])
        op.create_index("ix_rental_zubehoer_lines_rental_id", "rental_zubehoer_lines", ["rental_id"])
        op.create_index(
            "ix_rental_zubehoer_lines_catalog_item_id",
            "rental_zubehoer_lines",
            ["catalog_item_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "rental_zubehoer_lines" in tables:
        op.drop_table("rental_zubehoer_lines")
    if "rental_zubehoer_catalog" in tables:
        op.drop_table("rental_zubehoer_catalog")
