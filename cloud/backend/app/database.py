from pathlib import Path
import os
import uuid

from sqlalchemy import create_engine, inspect, text

from .roles import DEFAULT_HIRE_COMPANY_NAME, ROLE_MEMBER, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN
from sqlalchemy.orm import declarative_base, sessionmaker

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
    _add_column_if_missing(
        "users",
        "token_version",
        "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0",
    )
    appliance_columns = [
        ("name", "VARCHAR", "VARCHAR"),
        ("ip_address", "VARCHAR", "VARCHAR"),
        ("model", "VARCHAR", "VARCHAR"),
        ("comment", "VARCHAR", "VARCHAR"),
        ("escpos_feed_lines", "INTEGER", "INTEGER"),
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
        "events",
        "cash_registers_enabled",
        "ALTER TABLE events ADD COLUMN cash_registers_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS cash_registers_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "events",
        "vouchers_enabled",
        "ALTER TABLE events ADD COLUMN vouchers_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS vouchers_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    for table in ("hire_companies", "organisations", "events"):
        _add_column_if_missing(
            table,
            "receipt_printing_config",
            f"ALTER TABLE {table} ADD COLUMN receipt_printing_config TEXT",
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS receipt_printing_config JSON",
        )
        _add_column_if_missing(
            table,
            "receipt_logo_mime",
            f"ALTER TABLE {table} ADD COLUMN receipt_logo_mime VARCHAR(64)",
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS receipt_logo_mime VARCHAR(64)",
        )
        _add_column_if_missing(
            table,
            "receipt_logo_data",
            f"ALTER TABLE {table} ADD COLUMN receipt_logo_data TEXT",
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS receipt_logo_data TEXT",
        )
    _add_column_if_missing(
        "articles",
        "is_addition",
        "ALTER TABLE articles ADD COLUMN is_addition BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_addition BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "articles",
        "import_article_number",
        "ALTER TABLE articles ADD COLUMN import_article_number VARCHAR",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS import_article_number VARCHAR",
    )
    _add_column_if_missing(
        "articles",
        "description",
        "ALTER TABLE articles ADD COLUMN description TEXT",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS description TEXT",
    )
    _add_column_if_missing(
        "articles",
        "unit",
        "ALTER TABLE articles ADD COLUMN unit VARCHAR",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS unit VARCHAR",
    )
    _add_column_if_missing(
        "articles",
        "income_account",
        "ALTER TABLE articles ADD COLUMN income_account INTEGER",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS income_account INTEGER",
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
    _add_column_if_missing(
        "event_cash_registers",
        "pin",
        "ALTER TABLE event_cash_registers ADD COLUMN pin VARCHAR NOT NULL DEFAULT '0000'",
        "ALTER TABLE event_cash_registers ADD COLUMN IF NOT EXISTS pin VARCHAR NOT NULL DEFAULT '0000'",
    )
    _backfill_baseline_in_stock()
    _patch_entity_uuids("event_stations")
    _patch_entity_uuids("event_waiters")
    _patch_entity_uuids("event_app_layouts")
    _add_column_if_missing(
        "event_app_layout_cells",
        "voucher_definition_uuid",
        "ALTER TABLE event_app_layout_cells ADD COLUMN voucher_definition_uuid VARCHAR(36)",
        "ALTER TABLE event_app_layout_cells ADD COLUMN IF NOT EXISTS voucher_definition_uuid VARCHAR(36)",
    )
    _add_column_if_missing(
        "event_app_layout_cells",
        "voucher_definition_uuids",
        "ALTER TABLE event_app_layout_cells ADD COLUMN voucher_definition_uuids JSON NOT NULL DEFAULT '[]'",
        "ALTER TABLE event_app_layout_cells ADD COLUMN IF NOT EXISTS voucher_definition_uuids JSON NOT NULL DEFAULT '[]'",
    )
    _backfill_layout_cell_voucher_uuids()
    _ensure_appliance_pairing_sessions_table()
    _ensure_appliance_edge_credentials_table()
    _relax_appliances_organisation_id()
    _patch_hire_companies_tenancy()
    _patch_organisation_stripe_connect()


def _ensure_appliance_pairing_sessions_table() -> None:
    try:
        inspector = inspect(engine)
        if "appliance_pairing_sessions" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import AppliancePairingSession

    AppliancePairingSession.__table__.create(bind=engine, checkfirst=True)


def _ensure_appliance_edge_credentials_table() -> None:
    try:
        inspector = inspect(engine)
        if "appliance_edge_credentials" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import ApplianceEdgeCredential

    ApplianceEdgeCredential.__table__.create(bind=engine, checkfirst=True)


def _ensure_event_cash_registers_table() -> None:
    try:
        inspector = inspect(engine)
        if "event_cash_registers" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import EventCashRegister

    EventCashRegister.__table__.create(bind=engine, checkfirst=True)


def _patch_organisation_stripe_connect() -> None:
    """Stripe Connect status lives on the organisation payout boundary."""
    stripe_columns = [
        ("stripe_account_id", "VARCHAR(255)", "VARCHAR(255)"),
        ("stripe_charges_enabled", "BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("stripe_payouts_enabled", "BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("stripe_details_submitted", "BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("stripe_onboarding_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
        ("stripe_account_updated_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ]
    for col, sqlite_type, pg_type in stripe_columns:
        _add_column_if_missing(
            "organisations",
            col,
            f"ALTER TABLE organisations ADD COLUMN {col} {sqlite_type}",
            f"ALTER TABLE organisations ADD COLUMN IF NOT EXISTS {col} {pg_type}",
        )


def _backfill_layout_cell_voucher_uuids() -> None:
    try:
        inspector = inspect(engine)
        if "event_app_layout_cells" not in inspector.get_table_names():
            return
        col_names = {c["name"] for c in inspector.get_columns("event_app_layout_cells")}
    except Exception:
        return
    if "voucher_definition_uuids" not in col_names or "voucher_definition_uuid" not in col_names:
        return
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    "UPDATE event_app_layout_cells "
                    "SET voucher_definition_uuids = json_array(voucher_definition_uuid) "
                    "WHERE voucher_definition_uuid IS NOT NULL "
                    "AND trim(voucher_definition_uuid) != '' "
                    "AND (voucher_definition_uuids IS NULL OR voucher_definition_uuids = '[]')"
                )
            )
        else:
            conn.execute(
                text(
                    "UPDATE event_app_layout_cells "
                    "SET voucher_definition_uuids = json_build_array(voucher_definition_uuid) "
                    "WHERE voucher_definition_uuid IS NOT NULL "
                    "AND TRIM(voucher_definition_uuid) <> '' "
                    "AND ("
                    "voucher_definition_uuids IS NULL "
                    "OR voucher_definition_uuids::text = '[]'"
                    ")"
                )
            )


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


def _ensure_hire_companies_table() -> None:
    try:
        inspector = inspect(engine)
        if "hire_companies" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import HireCompany

    HireCompany.__table__.create(bind=engine, checkfirst=True)


def _patch_hire_companies_tenancy() -> None:
    """Multi-tenant: hire_companies + FK backfill (default Verleiher: Vendiqo)."""
    _ensure_hire_companies_table()
    _add_column_if_missing(
        "users",
        "role",
        "ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'member'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'member'",
    )
    _add_column_if_missing(
        "users",
        "hire_company_id",
        "ALTER TABLE users ADD COLUMN hire_company_id INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS hire_company_id INTEGER",
    )
    _add_column_if_missing(
        "organisations",
        "hire_company_id",
        "ALTER TABLE organisations ADD COLUMN hire_company_id INTEGER",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS hire_company_id INTEGER",
    )
    _add_column_if_missing(
        "appliances",
        "hire_company_id",
        "ALTER TABLE appliances ADD COLUMN hire_company_id INTEGER",
        "ALTER TABLE appliances ADD COLUMN IF NOT EXISTS hire_company_id INTEGER",
    )

    default_name = os.getenv("DEFAULT_HIRE_COMPANY_NAME", DEFAULT_HIRE_COMPANY_NAME).strip() or DEFAULT_HIRE_COMPANY_NAME
    is_sqlite = engine.dialect.name == "sqlite"

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM hire_companies WHERE name = :name LIMIT 1"),
            {"name": default_name},
        ).fetchone()
        if row:
            default_id = row[0]
        else:
            if is_sqlite:
                conn.execute(
                    text(
                        "INSERT INTO hire_companies (name) VALUES (:name)"
                    ),
                    {"name": default_name},
                )
                default_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
            else:
                inserted = conn.execute(
                    text("INSERT INTO hire_companies (name) VALUES (:name) RETURNING id"),
                    {"name": default_name},
                ).fetchone()
                default_id = inserted[0]

        conn.execute(
            text("UPDATE organisations SET hire_company_id = :hid WHERE hire_company_id IS NULL"),
            {"hid": default_id},
        )
        conn.execute(
            text("UPDATE appliances SET hire_company_id = :hid WHERE hire_company_id IS NULL"),
            {"hid": default_id},
        )
        if is_sqlite:
            conn.execute(
                text(
                    f"UPDATE users SET role = '{ROLE_PLATFORM_ADMIN}' "
                    "WHERE is_superuser = 1 AND (role IS NULL OR role = '' OR role = 'member')"
                ),
            )
            conn.execute(
                text(
                    f"UPDATE users SET role = '{ROLE_MEMBER}' WHERE role IS NULL OR role = ''"
                ),
            )
            conn.execute(
                text(
                    "UPDATE users SET hire_company_id = NULL "
                    f"WHERE role = '{ROLE_PLATFORM_ADMIN}' OR is_superuser = 1"
                ),
            )
        else:
            conn.execute(
                text(
                    f"UPDATE users SET role = '{ROLE_PLATFORM_ADMIN}' "
                    "WHERE is_superuser IS TRUE AND (role IS NULL OR role = '' OR role = 'member')"
                ),
            )
            conn.execute(
                text(
                    f"UPDATE users SET role = '{ROLE_MEMBER}' WHERE role IS NULL OR role = ''"
                ),
            )
            conn.execute(
                text(
                    "UPDATE users SET hire_company_id = NULL "
                    f"WHERE role = '{ROLE_PLATFORM_ADMIN}' OR is_superuser IS TRUE"
                ),
            )

    if not is_sqlite:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE organisations ALTER COLUMN hire_company_id SET NOT NULL"),
            )
            conn.execute(
                text("ALTER TABLE appliances ALTER COLUMN hire_company_id SET NOT NULL"),
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



def run_migrations() -> None:
    """Apply cloud Alembic migrations, fallback to metadata create_all."""
    try:
        from alembic import command
        from alembic.config import Config
        root = Path(__file__).resolve().parent.parent
        cfg = Config(str(root / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
        command.upgrade(cfg, "head")
    except Exception:
        Base.metadata.create_all(bind=engine)

