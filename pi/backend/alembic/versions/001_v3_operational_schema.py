"""v3 operational schema

Revision ID: 001_v3
Revises:
Create Date: 2026-05-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_v3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bundle_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=True),
        sa.Column("appliance_id", sa.Integer(), nullable=True),
        sa.Column("bundle_version", sa.String(length=64), nullable=True),
        sa.Column("pull_cursor", sa.String(length=255), nullable=True),
        sa.Column("pull_complete", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "synced_bundle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("json_body", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "event_order_counters",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_table(
        "event_pickup_counters",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_table(
        "register_display_states",
        sa.Column("cash_register_uuid", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("cash_register_uuid"),
    )
    op.create_index("ix_register_display_states_event_id", "register_display_states", ["event_id"])
    op.create_table(
        "payment_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_by_waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_batches_uuid", "payment_batches", ["uuid"], unique=True)
    op.create_index("ix_payment_batches_event_id", "payment_batches", ["event_id"])
    op.create_table(
        "order_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("table_number", sa.Integer(), nullable=True),
        sa.Column("pickup_code", sa.String(length=16), nullable=True),
        sa.Column("opened_by_waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("cash_register_uuid", sa.String(length=36), nullable=True),
        sa.Column("order_source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_sessions_event_id", "order_sessions", ["event_id"])
    op.create_table(
        "order_submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("client_order_id", sa.String(length=64), nullable=False),
        sa.Column("table_number", sa.Integer(), nullable=False),
        sa.Column("collective_batch_id", sa.Integer(), nullable=True),
        sa.Column("waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("order_source", sa.String(length=32), nullable=False),
        sa.Column("cash_register_uuid", sa.String(length=36), nullable=True),
        sa.Column("pickup_code", sa.String(length=16), nullable=True),
        sa.Column("pickup_status", sa.String(length=16), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_status", sa.String(length=16), nullable=False),
        sa.Column("print_status", sa.String(length=32), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_submissions_client_order_id", "order_submissions", ["client_order_id"], unique=True)
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("article_name", sa.String(length=255), nullable=False),
        sa.Column("note", sa.String(length=512), nullable=False),
        sa.Column("additions_json", sa.Text(), nullable=False),
        sa.Column("station_uuid", sa.String(length=36), nullable=True),
        sa.Column("origin_table_number", sa.Integer(), nullable=True),
        sa.Column("current_table_number", sa.Integer(), nullable=True),
        sa.Column("order_number", sa.Integer(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("client_line_key", sa.String(length=128), nullable=False),
        sa.Column("collective_batch_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_items_event_table_status",
        "order_items",
        ["event_id", "current_table_number", "status"],
    )
    op.create_table(
        "item_transfer_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("from_table", sa.Integer(), nullable=True),
        sa.Column("to_table", sa.Integer(), nullable=True),
        sa.Column("quantity_moved", sa.Integer(), nullable=False),
        sa.Column("moved_by_waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("table_number", sa.Integer(), nullable=True),
        sa.Column("invoice_number", sa.Integer(), nullable=True),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("payment_status", sa.String(length=16), nullable=False),
        sa.Column("payment_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("discount_cents", sa.Integer(), nullable=False),
        sa.Column("final_price_cents", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("cash_session_id", sa.Integer(), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("payment_batch_id", sa.Integer(), nullable=True),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("cash_tendered_cents", sa.Integer(), nullable=True),
        sa.Column("cash_change_cents", sa.Integer(), nullable=True),
        sa.Column("void_of_payment_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cash_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("cash_register_uuid", sa.String(length=36), nullable=False),
        sa.Column("operator_waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("opening_balance_cents", sa.Integer(), nullable=False),
        sa.Column("total_cash_cents", sa.Integer(), nullable=False),
        sa.Column("total_card_cents", sa.Integer(), nullable=False),
        sa.Column("counted_cash_cents", sa.Integer(), nullable=True),
        sa.Column("variance_cents", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sync_outbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_ids_json", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_outbox_chunk_id", "sync_outbox", ["chunk_id"], unique=True)
    op.create_table(
        "print_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("local_order_id", sa.Integer(), nullable=False),
        sa.Column("order_submission_id", sa.Integer(), nullable=True),
        sa.Column("station_uuid", sa.String(length=36), nullable=True),
        sa.Column("printer_host", sa.String(length=255), nullable=False),
        sa.Column("printer_port", sa.Integer(), nullable=False),
        sa.Column("escpos_payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("waiter_uuid", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kitchen_tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("local_order_id", sa.Integer(), nullable=False),
        sa.Column("order_submission_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("station_uuid", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kitchen_ticket_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("line_payload_json", sa.Text(), nullable=False),
        sa.Column("qty_total", sa.Integer(), nullable=False),
        sa.Column("qty_printed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    for table in (
        "kitchen_ticket_lines",
        "kitchen_tickets",
        "payment_receipts",
        "print_jobs",
        "sync_outbox",
        "cash_sessions",
        "payments",
        "invoice_items",
        "invoices",
        "item_transfer_log",
        "order_items",
        "order_submissions",
        "order_sessions",
        "payment_batches",
        "register_display_states",
        "event_pickup_counters",
        "event_order_counters",
        "synced_bundle",
        "bundle_meta",
    ):
        op.drop_table(table)
