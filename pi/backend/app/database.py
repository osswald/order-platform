import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _add_column_if_missing(table: str, column: str, ddl_sqlite: str, ddl_other: str) -> None:
    try:
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            return
        col_names = {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return
    if column in col_names:
        return
    is_sqlite = engine.dialect.name == "sqlite"
    stmt = ddl_sqlite if is_sqlite else ddl_other
    with engine.begin() as conn:
        conn.execute(text(stmt))


def _ensure_event_order_counters_table() -> None:
    try:
        inspector = inspect(engine)
        if "event_order_counters" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import EventOrderCounter

    EventOrderCounter.__table__.create(bind=engine, checkfirst=True)


def _ensure_event_pickup_counters_table() -> None:
    try:
        inspector = inspect(engine)
        if "event_pickup_counters" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import EventPickupCounter

    EventPickupCounter.__table__.create(bind=engine, checkfirst=True)


def _ensure_register_display_states_table() -> None:
    try:
        inspector = inspect(engine)
        if "register_display_states" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import RegisterDisplayState

    RegisterDisplayState.__table__.create(bind=engine, checkfirst=True)


def _ensure_collective_bills_table() -> None:
    """create_all() does not add new tables to existing databases."""
    try:
        inspector = inspect(engine)
        if "collective_bills" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import CollectiveBill

    CollectiveBill.__table__.create(bind=engine, checkfirst=True)


def _ensure_kitchen_tables() -> None:
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if {"kitchen_tickets", "kitchen_ticket_lines"}.issubset(tables):
            return
    except Exception:
        return
    from .models import KitchenTicket, KitchenTicketLine

    KitchenTicket.__table__.create(bind=engine, checkfirst=True)
    KitchenTicketLine.__table__.create(bind=engine, checkfirst=True)


def apply_schema_patches() -> None:
    """create_all() does not add columns or tables to existing databases."""
    _ensure_event_order_counters_table()
    _ensure_event_pickup_counters_table()
    _ensure_register_display_states_table()
    _ensure_collective_bills_table()
    _ensure_kitchen_tables()
    _add_column_if_missing(
        "local_orders",
        "table_number",
        "ALTER TABLE local_orders ADD COLUMN table_number INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS table_number INTEGER NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(
        "local_orders",
        "waiter_uuid",
        "ALTER TABLE local_orders ADD COLUMN waiter_uuid VARCHAR(36)",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS waiter_uuid VARCHAR(36)",
    )
    _add_column_if_missing(
        "print_jobs",
        "station_uuid",
        "ALTER TABLE print_jobs ADD COLUMN station_uuid VARCHAR(36)",
        "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS station_uuid VARCHAR(36)",
    )
    _add_column_if_missing(
        "local_orders",
        "payment_status",
        "ALTER TABLE local_orders ADD COLUMN payment_status VARCHAR(16) NOT NULL DEFAULT 'open'",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(16) NOT NULL DEFAULT 'open'",
    )
    _add_column_if_missing(
        "local_orders",
        "collective_bill_id",
        "ALTER TABLE local_orders ADD COLUMN collective_bill_id INTEGER",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS collective_bill_id INTEGER",
    )
    _add_column_if_missing(
        "local_orders",
        "order_source",
        "ALTER TABLE local_orders ADD COLUMN order_source VARCHAR(32) NOT NULL DEFAULT 'waiter'",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS order_source VARCHAR(32) NOT NULL DEFAULT 'waiter'",
    )
    _add_column_if_missing(
        "local_orders",
        "cash_register_uuid",
        "ALTER TABLE local_orders ADD COLUMN cash_register_uuid VARCHAR(36)",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS cash_register_uuid VARCHAR(36)",
    )
    _add_column_if_missing(
        "local_orders",
        "pickup_code",
        "ALTER TABLE local_orders ADD COLUMN pickup_code VARCHAR(16)",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS pickup_code VARCHAR(16)",
    )
    _add_column_if_missing(
        "local_orders",
        "pickup_status",
        "ALTER TABLE local_orders ADD COLUMN pickup_status VARCHAR(16)",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS pickup_status VARCHAR(16)",
    )
    _add_column_if_missing(
        "local_orders",
        "ready_at",
        "ALTER TABLE local_orders ADD COLUMN ready_at DATETIME",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS ready_at TIMESTAMP WITH TIME ZONE",
    )
    _add_column_if_missing(
        "local_orders",
        "picked_up_at",
        "ALTER TABLE local_orders ADD COLUMN picked_up_at DATETIME",
        "ALTER TABLE local_orders ADD COLUMN IF NOT EXISTS picked_up_at TIMESTAMP WITH TIME ZONE",
    )
