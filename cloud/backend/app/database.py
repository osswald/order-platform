import os
import uuid

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


def apply_schema_patches() -> None:
    """create_all() does not add columns to existing tables; patch known drift here."""
    _add_column_if_missing(
        "users",
        "name",
        "ALTER TABLE users ADD COLUMN name VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR",
    )
    _add_column_if_missing(
        "users",
        "event_admin_pin_hash",
        "ALTER TABLE users ADD COLUMN event_admin_pin_hash VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS event_admin_pin_hash VARCHAR(255)",
    )
    appliance_columns = [
        ("name", "VARCHAR", "VARCHAR"),
        ("ip_address", "VARCHAR", "VARCHAR"),
        ("model", "VARCHAR", "VARCHAR"),
        ("comment", "VARCHAR", "VARCHAR"),
    ]
    for col, sqlite_type, pg_type in appliance_columns:
        _add_column_if_missing(
            "appliances",
            col,
            f"ALTER TABLE appliances ADD COLUMN {col} {sqlite_type}",
            f"ALTER TABLE appliances ADD COLUMN IF NOT EXISTS {col} {pg_type}",
        )
    _add_column_if_missing(
        "appliances",
        "edge_client_id",
        "ALTER TABLE appliances ADD COLUMN edge_client_id VARCHAR(64)",
        "ALTER TABLE appliances ADD COLUMN IF NOT EXISTS edge_client_id VARCHAR(64)",
    )
    _add_column_if_missing(
        "appliances",
        "edge_secret_hash",
        "ALTER TABLE appliances ADD COLUMN edge_secret_hash VARCHAR(255)",
        "ALTER TABLE appliances ADD COLUMN IF NOT EXISTS edge_secret_hash VARCHAR(255)",
    )
    _add_column_if_missing(
        "events",
        "payment_mode",
        "ALTER TABLE events ADD COLUMN payment_mode VARCHAR(32) NOT NULL DEFAULT 'pay_later'",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS payment_mode VARCHAR(32) NOT NULL DEFAULT 'pay_later'",
    )
    _add_column_if_missing(
        "events",
        "payment_types",
        "ALTER TABLE events ADD COLUMN payment_types TEXT NOT NULL DEFAULT '[\"cash\"]'",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS payment_types JSON NOT NULL DEFAULT '[\"cash\"]'::json",
    )
    _add_column_if_missing(
        "events",
        "twint_qr_mime",
        "ALTER TABLE events ADD COLUMN twint_qr_mime VARCHAR(64)",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS twint_qr_mime VARCHAR(64)",
    )
    _add_column_if_missing(
        "events",
        "twint_qr_data",
        "ALTER TABLE events ADD COLUMN twint_qr_data TEXT",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS twint_qr_data TEXT",
    )
    _add_column_if_missing(
        "articles",
        "is_addition",
        "ALTER TABLE articles ADD COLUMN is_addition BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_addition BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "event_article_stock",
        "baseline_in_stock",
        "ALTER TABLE event_article_stock ADD COLUMN baseline_in_stock INTEGER",
        "ALTER TABLE event_article_stock ADD COLUMN IF NOT EXISTS baseline_in_stock INTEGER",
    )
    _add_column_if_missing(
        "event_stations",
        "kitchen_monitor_enabled",
        "ALTER TABLE event_stations ADD COLUMN kitchen_monitor_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE event_stations ADD COLUMN IF NOT EXISTS kitchen_monitor_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _ensure_event_cash_registers_table()
    _backfill_baseline_in_stock()
    _patch_entity_uuids("event_stations")
    _patch_entity_uuids("event_waiters")
    _patch_entity_uuids("event_app_layouts")
    _relax_appliances_organisation_id()


def _ensure_event_cash_registers_table() -> None:
    try:
        inspector = inspect(engine)
        if "event_cash_registers" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import EventCashRegister

    EventCashRegister.__table__.create(bind=engine, checkfirst=True)


def _backfill_baseline_in_stock() -> None:
    try:
        inspector = inspect(engine)
        if "event_article_stock" not in inspector.get_table_names():
            return
        col_names = {c["name"] for c in inspector.get_columns("event_article_stock")}
    except Exception:
        return
    if "baseline_in_stock" not in col_names:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE event_article_stock SET baseline_in_stock = in_stock "
                "WHERE baseline_in_stock IS NULL"
            )
        )


def _patch_entity_uuids(table: str) -> None:
    """Add uuid column and backfill existing rows."""
    _add_column_if_missing(
        table,
        "uuid",
        f"ALTER TABLE {table} ADD COLUMN uuid VARCHAR(36)",
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS uuid VARCHAR(36)",
    )
    try:
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            return
        col_names = {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return
    if "uuid" not in col_names:
        return
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        rows = conn.execute(text(f"SELECT id FROM {table} WHERE uuid IS NULL OR uuid = ''")).fetchall()
        for (row_id,) in rows:
            conn.execute(
                text(f"UPDATE {table} SET uuid = :u WHERE id = :id"),
                {"u": str(uuid.uuid4()), "id": row_id},
            )
        if not is_sqlite:
            conn.execute(
                text(f"ALTER TABLE {table} ALTER COLUMN uuid SET NOT NULL"),
            )


def _relax_appliances_organisation_id() -> None:
    """Legacy DBs had a required organisation_id; appliances no longer use it."""
    try:
        inspector = inspect(engine)
        if "appliances" not in inspector.get_table_names():
            return
        col_names = {c["name"] for c in inspector.get_columns("appliances")}
    except Exception:
        return
    if "organisation_id" not in col_names:
        return
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if is_sqlite:
            # SQLite cannot drop NOT NULL easily; column left unused on legacy DBs.
            return
        conn.execute(text("ALTER TABLE appliances ALTER COLUMN organisation_id DROP NOT NULL"))
