"""merge cloud alembic heads

Revision ID: 004_merge_cloud_heads
Revises: 003_edge_snapshots, 002_remove_legacy_appliance_edge_credentials
Create Date: 2026-06-24
"""

from typing import Sequence, Union

revision: str = "004_merge_cloud_heads"
down_revision: Union[str, Sequence[str], None] = (
    "003_edge_snapshots",
    "002_remove_legacy_appliance_edge_credentials",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
