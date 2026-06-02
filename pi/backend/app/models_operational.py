"""Normalized operational tables (v3)."""

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.ext.hybrid import hybrid_property

from .database import Base


class BundleMeta(Base):
    __tablename__ = "bundle_meta"
    id = Column(Integer, primary_key=True, default=1)
    organisation_id = Column(Integer, nullable=True)
    appliance_id = Column(Integer, nullable=True)
    bundle_version = Column(String(64), nullable=True)
    pull_cursor = Column(String(255), nullable=True)
    pull_complete = Column(Integer, nullable=False, default=0)
    last_pull_at = Column(DateTime(timezone=True), nullable=True)


class OrderSession(Base):
    __tablename__ = "order_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False, index=True)
    table_number = Column(Integer, nullable=True, index=True)
    pickup_code = Column(String(16), nullable=True, index=True)
    opened_by_waiter_uuid = Column(String(36), nullable=True)
    cash_register_uuid = Column(String(36), nullable=True, index=True)
    order_source = Column(String(32), nullable=False, default="waiter")
    status = Column(String(16), nullable=False, default="OPEN")
    guest_count = Column(Integer, nullable=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)


class OrderSubmission(Base):
    """One FERTIG / submit batch (replaces LocalOrder document)."""

    __tablename__ = "order_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    client_order_id = Column(String(64), nullable=False, unique=True, index=True)
    table_number = Column(Integer, nullable=False, default=0, index=True)
    collective_batch_id = Column(Integer, nullable=True, index=True)
    waiter_uuid = Column(String(36), nullable=True)
    order_source = Column(String(32), nullable=False, default="waiter")
    cash_register_uuid = Column(String(36), nullable=True, index=True)
    pickup_code = Column(String(16), nullable=True, index=True)
    pickup_status = Column(String(16), nullable=True, index=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    payment_status = Column(String(16), nullable=False, default="open")
    print_status = Column(String(32), nullable=False, default="pending")
    order_number = Column(Integer, nullable=True)
    ordered_at = Column(DateTime(timezone=True), nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @hybrid_property
    def collective_bill_id(self) -> int | None:
        return self.collective_batch_id

    @collective_bill_id.setter
    def collective_bill_id(self, value: int | None) -> None:
        self.collective_batch_id = value

    @collective_bill_id.expression
    def collective_bill_id(cls):
        return cls.collective_batch_id


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_event_table_status", "event_id", "current_table_number", "status"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, index=True)
    submission_id = Column(Integer, nullable=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    article_id = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_cents = Column(Integer, nullable=False, default=0)
    article_name = Column(String(255), nullable=False, default="")
    note = Column(String(512), nullable=False, default="")
    additions_json = Column(Text, nullable=False, default="[]")
    station_uuid = Column(String(36), nullable=True)
    origin_table_number = Column(Integer, nullable=True)
    current_table_number = Column(Integer, nullable=True)
    order_number = Column(Integer, nullable=True)
    ordered_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="OPEN")
    client_line_key = Column(String(128), nullable=False, index=True)
    collective_batch_id = Column(Integer, nullable=True, index=True)


class ItemTransferLog(Base):
    __tablename__ = "item_transfer_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, nullable=False, index=True)
    from_table = Column(Integer, nullable=True)
    to_table = Column(Integer, nullable=True)
    quantity_moved = Column(Integer, nullable=False, default=1)
    moved_by_waiter_uuid = Column(String(36), nullable=True)
    reason = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaymentBatch(Base):
    __tablename__ = "payment_batches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False, unique=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    created_by_waiter_uuid = Column(String(36), nullable=True)
    status = Column(String(16), nullable=False, default="open")
    total_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False, index=True)
    session_id = Column(Integer, nullable=True, index=True)
    table_number = Column(Integer, nullable=True)
    invoice_number = Column(Integer, nullable=True)
    total_cents = Column(Integer, nullable=False, default=0)
    payment_status = Column(String(16), nullable=False, default="OPEN")
    payment_batch_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, nullable=False, index=True)
    order_item_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_cents = Column(Integer, nullable=False, default=0)
    discount_cents = Column(Integer, nullable=False, default=0)
    final_price_cents = Column(Integer, nullable=False, default=0)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False, index=True)
    cash_session_id = Column(Integer, nullable=True, index=True)
    invoice_id = Column(Integer, nullable=True, index=True)
    payment_batch_id = Column(Integer, nullable=True, index=True)
    submission_id = Column(Integer, nullable=True, index=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    method = Column(String(32), nullable=False, default="cash")
    cash_tendered_cents = Column(Integer, nullable=True)
    cash_change_cents = Column(Integer, nullable=True)
    void_of_payment_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CashSession(Base):
    __tablename__ = "cash_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False, index=True)
    cash_register_uuid = Column(String(36), nullable=False, index=True)
    operator_waiter_uuid = Column(String(36), nullable=True)
    status = Column(String(16), nullable=False, default="OPEN")
    opening_balance_cents = Column(Integer, nullable=False, default=0)
    total_cash_cents = Column(Integer, nullable=False, default=0)
    total_card_cents = Column(Integer, nullable=False, default=0)
    counted_cash_cents = Column(Integer, nullable=True)
    variance_cents = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(36), nullable=False, unique=True, index=True)
    entity_type = Column(String(32), nullable=False)
    entity_ids_json = Column(Text, nullable=False, default="[]")
    event_id = Column(Integer, nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    payload_version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    acked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
