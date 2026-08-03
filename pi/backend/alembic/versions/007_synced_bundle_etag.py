"""Add etag column to synced_bundle for conditional cloud pulls."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_synced_bundle_etag"
down_revision: str | None = "006_cash_session_uuid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("synced_bundle", sa.Column("etag", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("synced_bundle", "etag")
