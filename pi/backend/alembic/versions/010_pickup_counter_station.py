"""Per-station pickup counters: composite PK (event_id, station_uuid).

Empty-string station_uuid is the event-wide (register-mode) counter row.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010_pickup_counter_station"
down_revision: str | None = "009_local_stock_overlay"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite cannot ALTER primary keys in place; rebuild the table.
    op.create_table(
        "event_pickup_counters_new",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("station_uuid", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("event_id", "station_uuid"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO event_pickup_counters_new (event_id, station_uuid, next_number)
            SELECT event_id, '', next_number FROM event_pickup_counters
            """
        )
    )
    op.drop_table("event_pickup_counters")
    op.rename_table("event_pickup_counters_new", "event_pickup_counters")


def downgrade() -> None:
    op.create_table(
        "event_pickup_counters_old",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO event_pickup_counters_old (event_id, next_number)
            SELECT event_id, MAX(next_number)
            FROM event_pickup_counters
            GROUP BY event_id
            """
        )
    )
    op.drop_table("event_pickup_counters")
    op.rename_table("event_pickup_counters_old", "event_pickup_counters")
