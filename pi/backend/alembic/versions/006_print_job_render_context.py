"""Add render_context_json for deferred ESC/POS PrintJob rendering."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_print_job_render_context"
down_revision: str | None = "005_station_pickups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("print_jobs", sa.Column("render_context_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("print_jobs", "render_context_json")
