import logging
import os

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

log = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_LEGACY_V3_TABLES = frozenset(
    {
        "bundle_meta",
        "synced_bundle",
        "submitted_orders",
        "order_sessions",
        "cash_sessions",
        "sync_outbox",
    }
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-8192")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=67108864")
    cursor.close()


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    try:
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            return
        if column in {c["name"] for c in inspector.get_columns(table)}:
            return
        with engine.begin() as conn:
            conn.execute(text(ddl))
    except Exception:
        log.exception("Failed to add column %s.%s", table, column)


def apply_shift_session_schema_patches() -> None:
    """create_all() does not alter existing tables; patch shift-session drift."""
    _add_column_if_missing(
        "cash_sessions",
        "subject_type",
        "ALTER TABLE cash_sessions ADD COLUMN subject_type VARCHAR(32) NOT NULL DEFAULT 'cash_register'",
    )
    _add_column_if_missing(
        "cash_sessions",
        "waiter_uuid",
        "ALTER TABLE cash_sessions ADD COLUMN waiter_uuid VARCHAR(36)",
    )
    _add_column_if_missing(
        "cash_sessions",
        "subject_name",
        "ALTER TABLE cash_sessions ADD COLUMN subject_name VARCHAR(128) NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        "cash_sessions",
        "wallet_cents",
        "ALTER TABLE cash_sessions ADD COLUMN wallet_cents INTEGER NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(
        "cash_sessions",
        "total_non_cash_cents",
        "ALTER TABLE cash_sessions ADD COLUMN total_non_cash_cents INTEGER NOT NULL DEFAULT 0",
    )
    try:
        inspector = inspect(engine)
        if "cash_sessions" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("cash_sessions")}
        if "subject_type" not in cols:
            return
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE cash_sessions SET subject_type = 'cash_register' "
                    "WHERE subject_type IS NULL OR subject_type = ''"
                )
            )
            if "wallet_cents" in cols:
                conn.execute(
                    text(
                        "UPDATE cash_sessions SET wallet_cents = opening_balance_cents "
                        "WHERE status = 'OPEN' AND (wallet_cents IS NULL OR wallet_cents = 0) "
                        "AND opening_balance_cents > 0"
                    )
                )
    except Exception:
        log.exception("Failed to backfill cash_sessions shift columns")


def _stamp_legacy_v3_baseline(cfg) -> None:
    """DBs created via create_all() have tables but no alembic_version — stamp before upgrade."""
    from alembic import command

    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
    except Exception:
        return
    if "alembic_version" in tables:
        return
    if not (_LEGACY_V3_TABLES & tables):
        return
    log.info("Stamping legacy Pi database at revision 001_v3 before upgrade")
    command.stamp(cfg, "001_v3")


def _create_all_tables() -> None:
    from . import models  # noqa: F401
    from . import models_operational  # noqa: F401

    Base.metadata.create_all(bind=engine)


def run_migrations() -> None:
    """Apply Alembic migrations to head; patch schema drift on existing SQLite DBs."""
    cfg = None
    try:
        from alembic import command
        from alembic.config import Config

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = Config(os.path.join(root, "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
        _stamp_legacy_v3_baseline(cfg)
        command.upgrade(cfg, "head")
    except Exception:
        log.exception("Alembic upgrade failed; applying shift-session schema patches")
    apply_shift_session_schema_patches()
    _create_all_tables()


def apply_schema_patches() -> None:
    """Deprecated: use run_migrations()."""
    run_migrations()
