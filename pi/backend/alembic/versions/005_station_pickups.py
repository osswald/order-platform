"""Station pickups table for per-station cash-register pickup codes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_station_pickups"
down_revision: str | None = "004_kitchen_ticket_printer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "station_pickups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("local_order_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("station_uuid", sa.String(length=36), nullable=True),
        sa.Column("pickup_code", sa.String(length=16), nullable=False),
        sa.Column("pickup_status", sa.String(length=16), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_station_pickups_local_order_id", "station_pickups", ["local_order_id"])
    op.create_index("ix_station_pickups_event_id", "station_pickups", ["event_id"])
    op.create_index("ix_station_pickups_station_uuid", "station_pickups", ["station_uuid"])
    op.create_index("ix_station_pickups_pickup_code", "station_pickups", ["pickup_code"])
    op.create_index("ix_station_pickups_pickup_status", "station_pickups", ["pickup_status"])


def downgrade() -> None:
    op.drop_index("ix_station_pickups_pickup_status", table_name="station_pickups")
    op.drop_index("ix_station_pickups_pickup_code", table_name="station_pickups")
    op.drop_index("ix_station_pickups_station_uuid", table_name="station_pickups")
    op.drop_index("ix_station_pickups_event_id", table_name="station_pickups")
    op.drop_index("ix_station_pickups_local_order_id", table_name="station_pickups")
    op.drop_table("station_pickups")
