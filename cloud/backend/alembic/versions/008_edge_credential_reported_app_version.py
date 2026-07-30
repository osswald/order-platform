"""Add reported Pi app version columns on appliance_edge_credentials.

Revision ID: 008_edge_credential_reported_app_version
Revises: 007_backfill_user_home_verleiher
Create Date: 2026-07-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_edge_credential_reported_app_version"
down_revision: Union[str, Sequence[str], None] = "007_backfill_user_home_verleiher"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "appliance_edge_credentials" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("appliance_edge_credentials")}
    if "reported_app_version" not in cols:
        op.add_column(
            "appliance_edge_credentials",
            sa.Column("reported_app_version", sa.String(64), nullable=True),
        )
    if "reported_app_build_time" not in cols:
        op.add_column(
            "appliance_edge_credentials",
            sa.Column("reported_app_build_time", sa.String(64), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "appliance_edge_credentials" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("appliance_edge_credentials")}
    if "reported_app_build_time" in cols:
        op.drop_column("appliance_edge_credentials", "reported_app_build_time")
    if "reported_app_version" in cols:
        op.drop_column("appliance_edge_credentials", "reported_app_version")
