"""Add etag column to synced_bundle for conditional cloud pulls.

Merges the parallel 006 heads from cash-session UUID and print-job render context.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_synced_bundle_etag"
down_revision: tuple[str, str] | None = (
    "006_cash_session_uuid",
    "006_print_job_render_context",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("synced_bundle", sa.Column("etag", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("synced_bundle", "etag")
