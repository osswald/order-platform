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


def apply_schema_patches() -> None:
    """create_all() does not add columns to existing tables."""
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
