"""Local SQLite state for on-prem Pi."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base
from .models_operational import (  # noqa: F401
    BundleMeta,
    CashSession,
    CashSessionLedger,
    Invoice,
    InvoiceItem,
    ItemTransferLog,
    OrderItem,
    OrderSession,
    OrderSubmission,
    Payment,
    PaymentBatch,
    SyncOutbox,
)

# v3 names used across the codebase
CollectiveBill = PaymentBatch
OutboxEntry = SyncOutbox
LocalOrder = OrderSubmission


class SyncedBundle(Base):
    """Single row cache of GET /edge/v1/bundle JSON."""

    __tablename__ = "synced_bundle"
    id = Column(Integer, primary_key=True, default=1)
    json_body = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EventOrderCounter(Base):
    __tablename__ = "event_order_counters"
    event_id = Column(Integer, primary_key=True)
    next_number = Column(Integer, nullable=False, default=1)


class EventPickupCounter(Base):
    __tablename__ = "event_pickup_counters"
    event_id = Column(Integer, primary_key=True)
    next_number = Column(Integer, nullable=False, default=1)


class RegisterDisplayState(Base):
    __tablename__ = "register_display_states"
    cash_register_uuid = Column(String(36), primary_key=True)
    event_id = Column(Integer, nullable=False, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PrintJob(Base):
    __tablename__ = "print_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    local_order_id = Column(Integer, nullable=False, index=True)
    order_submission_id = Column(Integer, nullable=True, index=True)
    station_uuid = Column(String(36), nullable=True)
    job_kind = Column(String(32), nullable=True)
    printer_host = Column(String(255), nullable=False)
    printer_port = Column(Integer, nullable=False, default=9100)
    escpos_payload = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="queued")
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmulatedReceipt(Base):
    __tablename__ = "emulated_receipts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_kind = Column(String(32), nullable=True)
    station_name = Column(String(255), nullable=True)
    escpos_payload = Column(Text, nullable=False)
    preview_text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False, index=True)
    payment_id = Column(Integer, nullable=True, index=True)
    waiter_uuid = Column(String(36), nullable=True, index=True)
    source_type = Column(String(32), nullable=False)
    source_id = Column(String(64), nullable=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KitchenTicket(Base):
    __tablename__ = "kitchen_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    local_order_id = Column(Integer, nullable=False, index=True)
    order_submission_id = Column(Integer, nullable=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    station_uuid = Column(String(36), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KitchenTicketLine(Base):
    __tablename__ = "kitchen_ticket_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, nullable=False, index=True)
    line_index = Column(Integer, nullable=False, default=0)
    line_payload_json = Column(Text, nullable=False)
    qty_total = Column(Integer, nullable=False)
    qty_printed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
