"""print_jobs.job_kind for waiter retry filtering

Revision ID: 003_print_job_kind
Revises: 002_shift_sessions
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_print_job_kind"
down_revision: Union[str, None] = "002_shift_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Plain ADD COLUMN is much faster on SQLite than batch_alter_table (full table copy).
    op.add_column("print_jobs", sa.Column("job_kind", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("print_jobs", "job_kind")
