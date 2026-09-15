"""Add render_context_json for deferred ESC/POS PrintJob rendering."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_print_job_render_context"
down_revision: str | None = "005_station_pickups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # Idempotent: runtime schema patches may have added this column already,
    # which previously blocked the merge upgrade past parallel 006 heads.
    if _has_column("print_jobs", "render_context_json"):
        return
    op.add_column("print_jobs", sa.Column("render_context_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if not _has_column("print_jobs", "render_context_json"):
        return
    op.drop_column("print_jobs", "render_context_json")
