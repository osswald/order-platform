"""Kitchen ticket printer column."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_kitchen_ticket_printer"
down_revision: Union[str, None] = "003_print_job_kind"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("kitchen_tickets", sa.Column("printer_appliance_id", sa.Integer(), nullable=True))
    op.create_index("ix_kitchen_tickets_printer_appliance_id", "kitchen_tickets", ["printer_appliance_id"])


def downgrade() -> None:
    op.drop_index("ix_kitchen_tickets_printer_appliance_id", table_name="kitchen_tickets")
    op.drop_column("kitchen_tickets", "printer_appliance_id")
