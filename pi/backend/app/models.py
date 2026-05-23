"""Local SQLite state for on-prem Pi."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class SyncedBundle(Base):
    """Single row cache of GET /edge/v1/bundle JSON."""

    __tablename__ = "synced_bundle"
    id = Column(Integer, primary_key=True, default=1)
    json_body = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LocalOrder(Base):
    __tablename__ = "local_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_order_id = Column(String(64), nullable=False, unique=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    table_number = Column(Integer, nullable=False, index=True)
    waiter_uuid = Column(String(36), nullable=True)
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
