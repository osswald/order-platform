"""Add rentals table and require appliance_lendings.rental_id.

Revision ID: 012_rentals_and_lending_rental_id
Revises: 011_edge_submitted_order_collective_bill_uuid
Create Date: 2026-08-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.rental_backfill import backfill_appliance_lending_rentals

revision: str = "012_rentals_and_lending_rental_id"
down_revision: Union[str, Sequence[str], None] = "011_edge_submitted_order_collective_bill_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RANGE_INDEX = "ix_rentals_hire_company_id_start_date_end_date"
ORG_INDEX = "ix_rentals_organisation_id_start_date"
RENTAL_ID_INDEX = "ix_appliance_lendings_rental_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "organisations" not in tables or "appliance_lendings" not in tables:
        return

    if "rentals" not in tables:
        op.create_table(
            "rentals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("hire_company_id", sa.Integer(), sa.ForeignKey("hire_companies.id"), nullable=False),
            sa.Column("organisation_id", sa.Integer(), sa.ForeignKey("organisations.id"), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=True),
        )
        op.create_index("ix_rentals_id", "rentals", ["id"])
        op.create_index("ix_rentals_hire_company_id", "rentals", ["hire_company_id"])
        op.create_index("ix_rentals_organisation_id", "rentals", ["organisation_id"])
        op.create_index(RANGE_INDEX, "rentals", ["hire_company_id", "start_date", "end_date"])
        op.create_index(ORG_INDEX, "rentals", ["organisation_id", "start_date"])

    lending_cols = {col["name"] for col in inspector.get_columns("appliance_lendings")}
    if "rental_id" not in lending_cols:
        op.add_column("appliance_lendings", sa.Column("rental_id", sa.Integer(), nullable=True))

    backfill_appliance_lending_rentals(bind)

    lending_indexes = {idx["name"] for idx in inspector.get_indexes("appliance_lendings")}
    if RENTAL_ID_INDEX not in lending_indexes:
        op.create_index(RENTAL_ID_INDEX, "appliance_lendings", ["rental_id"])

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("appliance_lendings")}
    if "fk_appliance_lendings_rental_id_rentals" not in fk_names:
        op.create_foreign_key(
            "fk_appliance_lendings_rental_id_rentals",
            "appliance_lendings",
            "rentals",
            ["rental_id"],
            ["id"],
        )

    leftover = bind.execute(sa.text("SELECT COUNT(*) FROM appliance_lendings WHERE rental_id IS NULL")).scalar()
    if leftover:
        raise RuntimeError(f"appliance_lendings.rental_id backfill left {leftover} null rows")

    if bind.dialect.name != "sqlite":
        op.alter_column("appliance_lendings", "rental_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "appliance_lendings" in tables:
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("appliance_lendings")}
        if "fk_appliance_lendings_rental_id_rentals" in fk_names:
            op.drop_constraint("fk_appliance_lendings_rental_id_rentals", "appliance_lendings", type_="foreignkey")
        index_names = {idx["name"] for idx in inspector.get_indexes("appliance_lendings")}
        if RENTAL_ID_INDEX in index_names:
            op.drop_index(RENTAL_ID_INDEX, table_name="appliance_lendings")
        cols = {col["name"] for col in inspector.get_columns("appliance_lendings")}
        if "rental_id" in cols:
            op.drop_column("appliance_lendings", "rental_id")
    if "rentals" in tables:
        op.drop_table("rentals")
