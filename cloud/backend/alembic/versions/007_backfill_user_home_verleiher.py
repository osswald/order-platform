"""Backfill user home Verleiher (hire_company_id) from organisations.

Revision ID: 007_backfill_user_home_verleiher
Revises: 006_edge_order_items_ordered_at
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_backfill_user_home_verleiher"
down_revision: Union[str, Sequence[str], None] = "006_edge_order_items_ordered_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mirror of app.database._backfill_user_home_verleiher for deploy-time alembic runs.
    # Idempotent: only fills NULL hire_company_id for member / organisation_admin with a
    # single Verleiher across organisation links. Platform admins and true orphans skipped.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names = set(inspector.get_table_names())
    if not {"users", "organisations", "organisation_users"}.issubset(names):
        return
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    if "hire_company_id" not in user_cols or "role" not in user_cols:
        return

    op.execute(
        """
        UPDATE users
        SET hire_company_id = (
            SELECT o.hire_company_id
            FROM organisation_users ou
            JOIN organisations o ON o.id = ou.organisation_id
            WHERE ou.user_id = users.id
            LIMIT 1
        )
        WHERE hire_company_id IS NULL
          AND role IN ('member', 'organisation_admin')
          AND COALESCE(is_superuser, FALSE) IS FALSE
          AND id IN (
            SELECT ou.user_id
            FROM organisation_users ou
            JOIN organisations o ON o.id = ou.organisation_id
            GROUP BY ou.user_id
            HAVING COUNT(DISTINCT o.hire_company_id) = 1
          )
        """
    )


def downgrade() -> None:
    # Irreversible data backfill — cannot know which rows were previously NULL.
    pass
