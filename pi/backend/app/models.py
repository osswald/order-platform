"""Local SQLite state for on-prem Pi."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class SyncedBundle(Base):
    """Single row cache of GET /edge/v1/bundle JSON."""

    __tablename__ = "synced_bundle"
    id = Column(Integer, primary_key=True, default=1)
    json_body = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EventOrderCounter(Base):
    """Per-event monotonic order number sequence (FERTIG submissions only)."""

    __tablename__ = "event_order_counters"
    event_id = Column(Integer, primary_key=True)
    next_number = Column(Integer, nullable=False, default=1)


class EventPickupCounter(Base):
    """Per-event monotonic pickup code number sequence for cash-register orders."""

    __tablename__ = "event_pickup_counters"
    event_id = Column(Integer, primary_key=True)
    next_number = Column(Integer, nullable=False, default=1)


class RegisterDisplayState(Base):
    __tablename__ = "register_display_states"
    cash_register_uuid = Column(String(36), primary_key=True)
    event_id = Column(Integer, nullable=False, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CollectiveBill(Base):
    __tablename__ = "collective_bills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False, unique=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LocalOrder(Base):
    __tablename__ = "local_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_order_id = Column(String(64), nullable=False, unique=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    table_number = Column(Integer, nullable=True, index=True)
    collective_bill_id = Column(Integer, nullable=True, index=True)
    waiter_uuid = Column(String(36), nullable=True)
    order_source = Column(String(32), nullable=False, default="waiter")
    cash_register_uuid = Column(String(36), nullable=True, index=True)
    pickup_code = Column(String(16), nullable=True, index=True)
    pickup_status = Column(String(16), nullable=True, index=True)  # pending | ready | picked_up
    ready_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    payment_status = Column(String(16), nullable=False, default="open")  # open | paid
    payload_json = Column(Text, nullable=False)
    print_status = Column(String(32), nullable=False, default="pending")  # pending | done | error
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OutboxEntry(Base):
    """Orders not yet acknowledged by cloud."""

    __tablename__ = "outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_order_id = Column(String(64), nullable=False, unique=True, index=True)
    event_id = Column(Integer, nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")  # pending | sent | error
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PrintJob(Base):
    __tablename__ = "print_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    local_order_id = Column(Integer, nullable=False, index=True)
    station_uuid = Column(String(36), nullable=True)
    printer_host = Column(String(255), nullable=False)
    printer_port = Column(Integer, nullable=False, default=9100)
    escpos_payload = Column(Text, nullable=False)  # base64
    status = Column(String(32), nullable=False, default="queued")  # queued | sent | error
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KitchenTicket(Base):
    __tablename__ = "kitchen_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    local_order_id = Column(Integer, nullable=False, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    station_uuid = Column(String(36), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="open")  # open | partial | done
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
