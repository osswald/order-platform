import logging
import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .env import is_production
from .roles import DEFAULT_HIRE_COMPANY_NAME, ROLE_MEMBER, ROLE_PLATFORM_ADMIN

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

log = logging.getLogger(__name__)


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
    _add_column_if_missing(
        "users",
        "theme_preference",
        "ALTER TABLE users ADD COLUMN theme_preference VARCHAR(16) NOT NULL DEFAULT 'system'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(16) NOT NULL DEFAULT 'system'",
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
        "instant_collective_bill_name",
        "ALTER TABLE events ADD COLUMN instant_collective_bill_name VARCHAR(128)",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS instant_collective_bill_name VARCHAR(128)",
    )
    _add_column_if_missing(
        "events",
        "instant_collective_bill_uuid",
        "ALTER TABLE events ADD COLUMN instant_collective_bill_uuid VARCHAR(36)",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS instant_collective_bill_uuid VARCHAR(36)",
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
        "shift_settlement_enabled",
        "ALTER TABLE events ADD COLUMN shift_settlement_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS shift_settlement_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "events",
        "vouchers_enabled",
        "ALTER TABLE events ADD COLUMN vouchers_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS vouchers_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "events",
        "discounts_enabled",
        "ALTER TABLE events ADD COLUMN discounts_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS discounts_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "events",
        "offer_payment_receipt",
        "ALTER TABLE events ADD COLUMN offer_payment_receipt BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS offer_payment_receipt BOOLEAN NOT NULL DEFAULT FALSE",
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
        "is_active",
        "ALTER TABLE articles ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
    )
    _add_column_if_missing(
        "article_addition_links",
        "preselected",
        "ALTER TABLE article_addition_links ADD COLUMN preselected BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE article_addition_links ADD COLUMN IF NOT EXISTS preselected BOOLEAN NOT NULL DEFAULT FALSE",
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
    _add_column_if_missing(
        "appliances",
        "is_hosted_virtual",
        "ALTER TABLE appliances ADD COLUMN is_hosted_virtual BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE appliances ADD COLUMN IF NOT EXISTS is_hosted_virtual BOOLEAN NOT NULL DEFAULT FALSE",
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
    _add_column_if_missing(
        "events",
        "alternative_printers_enabled",
        "ALTER TABLE events ADD COLUMN alternative_printers_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS alternative_printers_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "events",
        "kitchen_monitors_enabled",
        "ALTER TABLE events ADD COLUMN kitchen_monitors_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS kitchen_monitors_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _ensure_event_station_printer_rules_table()
    _ensure_event_kitchen_monitor_printers_table()
    _backfill_kitchen_monitors_from_stations()
    _ensure_appliance_pairing_sessions_table()
    _ensure_appliance_edge_credentials_table()
    _relax_appliances_organisation_id()
    _patch_hire_companies_tenancy()
    _patch_organisation_stripe_connect()
    _patch_organisation_currency()
    _patch_tenant_admin_role()
    _ensure_countries_table()
    _seed_countries()
    _patch_country_reference_columns()
    _backfill_country_ids()
    _drop_legacy_country_columns()
    _ensure_tax_codes_table()
    _seed_tax_codes()
    _ensure_keine_tax_codes()
    _ensure_payment_types_table()
    _seed_payment_types()
    _refresh_payment_types_cache()
    _ensure_accounting_accounts_tables()
    _add_column_if_missing(
        "organisations",
        "accounts_enabled",
        "ALTER TABLE organisations ADD COLUMN accounts_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS accounts_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "article_categories",
        "accounting_account_id",
        "ALTER TABLE article_categories ADD COLUMN accounting_account_id INTEGER",
        "ALTER TABLE article_categories ADD COLUMN IF NOT EXISTS accounting_account_id INTEGER",
    )
    _add_column_if_missing(
        "articles",
        "accounting_account_id",
        "ALTER TABLE articles ADD COLUMN accounting_account_id INTEGER",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS accounting_account_id INTEGER",
    )
    _drop_column_if_present("articles", "income_account")
    _drop_column_if_present("articles", "monitor_stock")
    _drop_column_if_present("articles", "in_stock")
    _add_column_if_missing(
        "organisations",
        "vat_liable",
        "ALTER TABLE organisations ADD COLUMN vat_liable BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS vat_liable BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _add_column_if_missing(
        "organisations",
        "default_tax_code_id",
        "ALTER TABLE organisations ADD COLUMN default_tax_code_id INTEGER",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS default_tax_code_id INTEGER",
    )
    _add_column_if_missing(
        "articles",
        "tax_code_id",
        "ALTER TABLE articles ADD COLUMN tax_code_id INTEGER",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS tax_code_id INTEGER",
    )
    _patch_edge_order_item_fiscal_columns()
    _patch_edge_operational_snapshot_tables()
    _patch_event_waiter_register_subsidiary_columns()
    _ensure_accounting_tax_code_defaults_table()
    _add_column_if_missing(
        "organisations",
        "position_comments_enabled",
        "ALTER TABLE organisations ADD COLUMN position_comments_enabled BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS position_comments_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _ensure_organisation_position_comments_table()


def _patch_edge_operational_snapshot_tables() -> None:
    """Pi restore snapshots and org-scoped cash session keys (Alembic 003 drift)."""
    try:
        from .models import EdgeCashSession, EdgeKitchenTicketSnapshot, EdgeOrderSnapshot

        EdgeOrderSnapshot.__table__.create(bind=engine, checkfirst=True)
        EdgeKitchenTicketSnapshot.__table__.create(bind=engine, checkfirst=True)
        EdgeCashSession.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        return
    _add_column_if_missing(
        "edge_cash_sessions",
        "subject_key",
        "ALTER TABLE edge_cash_sessions ADD COLUMN subject_key VARCHAR(128)",
        "ALTER TABLE edge_cash_sessions ADD COLUMN IF NOT EXISTS subject_key VARCHAR(128)",
    )
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_edge_cash_sessions_subject_key "
                "ON edge_cash_sessions (subject_key)"
            )
        )
        if not is_sqlite:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_edge_cash_sessions_org_event_subject "
                    "ON edge_cash_sessions (organisation_id, event_id, subject_key)"
                )
            )


def _patch_edge_order_item_fiscal_columns() -> None:
    columns = [
        ("cash_register_uuid", "VARCHAR(36)", "VARCHAR(36)"),
        ("order_source", "VARCHAR(32)", "VARCHAR(32)"),
        ("tax_code_id", "INTEGER", "INTEGER"),
        ("tax_rate_percent", "FLOAT", "DOUBLE PRECISION"),
        ("accounting_account_id", "INTEGER", "INTEGER"),
        ("net_cents", "INTEGER", "INTEGER"),
        ("vat_cents", "INTEGER", "INTEGER"),
    ]
    for name, sqlite_type, pg_type in columns:
        _add_column_if_missing(
            "edge_order_items",
            name,
            f"ALTER TABLE edge_order_items ADD COLUMN {name} {sqlite_type}",
            f"ALTER TABLE edge_order_items ADD COLUMN IF NOT EXISTS {name} {pg_type}",
        )


def _patch_event_waiter_register_subsidiary_columns() -> None:
    for table in ("event_waiters", "event_cash_registers"):
        _add_column_if_missing(
            table,
            "subsidiary_code",
            f"ALTER TABLE {table} ADD COLUMN subsidiary_code VARCHAR(32)",
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS subsidiary_code VARCHAR(32)",
        )


def _ensure_organisation_position_comments_table() -> None:
    try:
        inspector = inspect(engine)
        if "organisation_position_comments" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import OrganisationPositionComment

    OrganisationPositionComment.__table__.create(bind=engine, checkfirst=True)


def _ensure_accounting_tax_code_defaults_table() -> None:
    from sqlalchemy import inspect

    insp = inspect(engine)
    names = set(insp.get_table_names())
    if "accounting_account_tax_code_defaults" in names:
        return
    from .models import AccountingAccountTaxCodeDefault

    AccountingAccountTaxCodeDefault.__table__.create(bind=engine, checkfirst=True)


def _patch_tenant_admin_role() -> None:
    """Rename legacy org_admin role slug to tenant_admin."""
    try:
        inspector = inspect(engine)
        if "users" not in inspector.get_table_names():
            return
    except Exception:
        return
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET role = 'tenant_admin' WHERE role = 'org_admin'"))


def _ensure_event_station_printer_rules_table() -> None:
    try:
        inspector = inspect(engine)
        if "event_station_printer_rules" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import EventStationPrinterRule

    EventStationPrinterRule.__table__.create(bind=engine, checkfirst=True)


def _ensure_event_kitchen_monitor_printers_table() -> None:
    try:
        inspector = inspect(engine)
        if "event_kitchen_monitor_printers" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import EventKitchenMonitorPrinter

    EventKitchenMonitorPrinter.__table__.create(bind=engine, checkfirst=True)


def _backfill_kitchen_monitors_from_stations() -> None:
    """Migrate legacy station kitchen_monitor_enabled to event-level kitchen monitors."""
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "event_stations" not in tables or "event_kitchen_monitor_printers" not in tables:
            return
        if "kitchen_monitor_enabled" not in {c["name"] for c in inspector.get_columns("event_stations")}:
            return
    except Exception:
        return
    from .models import Event, EventKitchenMonitorPrinter, EventStation

    db = SessionLocal()
    try:
        stations = (
            db.query(EventStation)
            .filter(EventStation.kitchen_monitor_enabled.is_(True))
            .filter(EventStation.printer_appliance_id.isnot(None))
            .all()
        )
        if not stations:
            return
        event_ids = {st.event_id for st in stations}
        for event_id in event_ids:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                continue
            if not bool(getattr(event, "kitchen_monitors_enabled", False)):
                event.kitchen_monitors_enabled = True
            existing = {
                row.printer_appliance_id
                for row in db.query(EventKitchenMonitorPrinter)
                .filter(EventKitchenMonitorPrinter.event_id == event_id)
                .all()
            }
            sort_order = len(existing)
            for st in stations:
                if st.event_id != event_id or st.printer_appliance_id in existing:
                    continue
                db.add(
                    EventKitchenMonitorPrinter(
                        event_id=event_id,
                        printer_appliance_id=st.printer_appliance_id,
                        sort_order=sort_order,
                        label=st.name,
                    )
                )
                existing.add(st.printer_appliance_id)
                sort_order += 1
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Failed to backfill kitchen monitor printers from stations")
    finally:
        db.close()


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


def _patch_organisation_currency() -> None:
    """Currency belongs on the organisation; backfill from each org's most recent event."""
    _add_column_if_missing(
        "organisations",
        "currency",
        "ALTER TABLE organisations ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'EUR'",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'EUR'",
    )
    try:
        inspector = inspect(engine)
        if "organisations" not in inspector.get_table_names():
            return
        if "events" not in inspector.get_table_names():
            return
        event_cols = {c["name"] for c in inspector.get_columns("events")}
    except Exception:
        return
    if "currency" not in event_cols:
        return
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(
                text(
                    "UPDATE organisations SET currency = ("
                    "SELECT e.currency FROM events e "
                    "WHERE e.organisation_id = organisations.id "
                    "ORDER BY e.id DESC LIMIT 1"
                    ") WHERE EXISTS ("
                    "SELECT 1 FROM events e WHERE e.organisation_id = organisations.id"
                    ")"
                )
            )
        else:
            conn.execute(
                text(
                    "UPDATE organisations o SET currency = sub.currency "
                    "FROM ("
                    "SELECT DISTINCT ON (organisation_id) organisation_id, currency "
                    "FROM events ORDER BY organisation_id, id DESC"
                    ") sub "
                    "WHERE sub.organisation_id = o.id"
                )
            )
    _drop_column_if_present("events", "currency")


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



def _drop_column_if_present(table: str, column: str) -> None:
    try:
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            return
        col_names = {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return
    if column not in col_names:
        return
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
        else:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}"))


def _ensure_countries_table() -> None:
    try:
        inspector = inspect(engine)
        if "countries" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import Country

    Country.__table__.create(bind=engine, checkfirst=True)


def _seed_countries() -> None:
    from .models import Country
    from .reference_countries import SEEDED_COUNTRIES

    db = SessionLocal()
    try:
        if db.query(Country.id).first() is not None:
            return
        for code, name in SEEDED_COUNTRIES:
            db.add(Country(code=code, name=name))
        db.commit()
    finally:
        db.close()


def _patch_country_reference_columns() -> None:
    _add_column_if_missing(
        "organisations",
        "country_id",
        "ALTER TABLE organisations ADD COLUMN country_id INTEGER REFERENCES countries(id)",
        "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS country_id INTEGER REFERENCES countries(id)",
    )
    _add_column_if_missing(
        "hire_companies",
        "country_id",
        "ALTER TABLE hire_companies ADD COLUMN country_id INTEGER REFERENCES countries(id)",
        "ALTER TABLE hire_companies ADD COLUMN IF NOT EXISTS country_id INTEGER REFERENCES countries(id)",
    )


def _backfill_country_ids() -> None:
    from .reference_countries import resolve_legacy_country_code

    try:
        inspector = inspect(engine)
        if "countries" not in inspector.get_table_names():
            return
    except Exception:
        return

    db = SessionLocal()
    try:
        from .models import Country

        code_to_id = {country.code: country.id for country in db.query(Country).all()}
    finally:
        db.close()
    if not code_to_id:
        return

    def _country_id_for_value(value: str | None, *, default_code: str | None) -> int | None:
        code = resolve_legacy_country_code(value, default_code=default_code)
        if code is None:
            return None
        return code_to_id.get(code)

    try:
        inspector = inspect(engine)
        org_cols = {c["name"] for c in inspector.get_columns("organisations")}
        hire_cols = {c["name"] for c in inspector.get_columns("hire_companies")}
    except Exception:
        return

    with engine.begin() as conn:
        if "country" in org_cols and "country_id" in org_cols:
            rows = conn.execute(text("SELECT id, country, country_id FROM organisations")).fetchall()
            for row_id, legacy_country, country_id in rows:
                if country_id is not None:
                    continue
                resolved = _country_id_for_value(legacy_country, default_code="CH")
                if resolved is not None:
                    conn.execute(
                        text("UPDATE organisations SET country_id = :country_id WHERE id = :id"),
                        {"country_id": resolved, "id": row_id},
                    )
        if "country" in hire_cols and "country_id" in hire_cols:
            rows = conn.execute(text("SELECT id, country, country_id FROM hire_companies")).fetchall()
            for row_id, legacy_country, country_id in rows:
                if country_id is not None:
                    continue
                resolved = _country_id_for_value(legacy_country, default_code=None)
                conn.execute(
                    text("UPDATE hire_companies SET country_id = :country_id WHERE id = :id"),
                    {"country_id": resolved, "id": row_id},
                )


def _drop_legacy_country_columns() -> None:
    _drop_column_if_present("organisations", "country")
    _drop_column_if_present("hire_companies", "country")


def _ensure_tax_codes_table() -> None:
    try:
        inspector = inspect(engine)
        if "tax_codes" in inspector.get_table_names() and "tax_code_rates" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import TaxCode, TaxCodeRate

    TaxCode.__table__.create(bind=engine, checkfirst=True)
    TaxCodeRate.__table__.create(bind=engine, checkfirst=True)


def _seed_tax_codes() -> None:
    from datetime import date

    from .models import Country, TaxCode, TaxCodeRate

    seed_rows: list[tuple[str, str, float, date]] = [
        ("DE", "Normalsatz", 19.0, date(2007, 1, 1)),
        ("DE", "Ermäßigter Satz", 7.0, date(2007, 1, 1)),
        ("AT", "Normalsatz", 20.0, date(2007, 1, 1)),
        ("AT", "Ermäßigter Satz", 10.0, date(2007, 1, 1)),
        ("AT", "Ermäßigter Satz 13%", 13.0, date(2007, 1, 1)),
        ("CH", "Normalsatz", 8.1, date(2024, 1, 1)),
        ("CH", "Reduzierter Satz", 2.6, date(2024, 1, 1)),
        ("CH", "Sondersatz Beherbergung", 3.8, date(2024, 1, 1)),
        ("FR", "Taux normal", 20.0, date(2014, 1, 1)),
        ("FR", "Taux réduit", 5.5, date(2014, 1, 1)),
        ("FR", "Taux intermédiaire", 10.0, date(2014, 1, 1)),
        ("FR", "Taux super-réduit", 2.1, date(2014, 1, 1)),
        ("IT", "Aliquota ordinaria", 22.0, date(2013, 10, 1)),
        ("IT", "Aliquota ridotta", 10.0, date(2013, 10, 1)),
        ("IT", "Aliquota ridotta 5%", 5.0, date(2013, 10, 1)),
        ("IT", "Aliquota super-ridotta", 4.0, date(2013, 10, 1)),
        ("BE", "Taux normal", 21.0, date(2014, 1, 1)),
        ("BE", "Taux réduit", 6.0, date(2014, 1, 1)),
        ("BE", "Taux réduit 12%", 12.0, date(2014, 1, 1)),
        ("NL", "Hoog tarief", 21.0, date(2019, 1, 1)),
        ("NL", "Laag tarief", 9.0, date(2019, 1, 1)),
        ("DE", "Keine", 0.0, date(2007, 1, 1)),
        ("AT", "Keine", 0.0, date(2007, 1, 1)),
        ("CH", "Keine", 0.0, date(2007, 1, 1)),
        ("FR", "Keine", 0.0, date(2007, 1, 1)),
        ("IT", "Keine", 0.0, date(2007, 1, 1)),
        ("BE", "Keine", 0.0, date(2007, 1, 1)),
        ("NL", "Keine", 0.0, date(2007, 1, 1)),
    ]

    db = SessionLocal()
    try:
        if db.query(TaxCode.id).first() is not None:
            return
        code_to_id = {country.code: country.id for country in db.query(Country).all()}
        for country_code, name, rate_percent, valid_from in seed_rows:
            country_id = code_to_id.get(country_code)
            if country_id is None:
                continue
            tax_code = TaxCode(country_id=country_id, name=name)
            tax_code.rates.append(
                TaxCodeRate(
                    rate_percent=rate_percent,
                    valid_from=valid_from,
                    valid_to=None,
                )
            )
            db.add(tax_code)
        db.commit()
    finally:
        db.close()


def _ensure_keine_tax_codes() -> None:
    """Backfill 0% 'Keine' tax code for the seven reference countries only."""
    from datetime import date

    from .models import Country, TaxCode, TaxCodeRate
    from .reference_countries import SEEDED_COUNTRIES

    db = SessionLocal()
    try:
        reference_codes = [code for code, _ in SEEDED_COUNTRIES]
        countries = db.query(Country).filter(Country.code.in_(reference_codes)).all()
        for country in countries:
            exists = (
                db.query(TaxCode.id)
                .filter(TaxCode.country_id == country.id, TaxCode.name == "Keine")
                .first()
            )
            if exists is not None:
                continue
            tax_code = TaxCode(country_id=country.id, name="Keine")
            tax_code.rates.append(
                TaxCodeRate(
                    rate_percent=0.0,
                    valid_from=date(2007, 1, 1),
                    valid_to=None,
                )
            )
            db.add(tax_code)
        db.commit()
    finally:
        db.close()


def _ensure_payment_types_table() -> None:
    try:
        inspector = inspect(engine)
        if "payment_types" in inspector.get_table_names():
            return
    except Exception:
        return
    from .models import PaymentType

    PaymentType.__table__.create(bind=engine, checkfirst=True)


def _seed_payment_types() -> None:
    from .models import PaymentType

    seed_rows = [
        ("cash", 0),
        ("twint", 1),
        ("sumup", 2),
        ("stripe_terminal", 3),
    ]
    db = SessionLocal()
    try:
        if db.query(PaymentType.id).first() is not None:
            return
        for slug, sort_order in seed_rows:
            db.add(PaymentType(slug=slug, sort_order=sort_order, is_active=True))
        db.commit()
    finally:
        db.close()


def _refresh_payment_types_cache() -> None:
    from .payment_types_config import refresh_payment_types_cache

    db = SessionLocal()
    try:
        refresh_payment_types_cache(db)
    finally:
        db.close()


def _ensure_accounting_accounts_tables() -> None:
    try:
        inspector = inspect(engine)
        names = set(inspector.get_table_names())
        if "accounting_accounts" in names and "accounting_account_payment_type_defaults" in names:
            return
    except Exception:
        return
    from .models import AccountingAccount, AccountingAccountPaymentTypeDefault

    AccountingAccount.__table__.create(bind=engine, checkfirst=True)
    AccountingAccountPaymentTypeDefault.__table__.create(bind=engine, checkfirst=True)


def _alembic_current_revision() -> str | None:
    try:
        inspector = inspect(engine)
        if "alembic_version" not in inspector.get_table_names():
            return None
        with engine.begin() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
        if not row or not row[0]:
            return None
        return str(row[0])
    except Exception:
        return None


def _database_pre_alembic() -> bool:
    try:
        inspector = inspect(engine)
        if "users" not in inspector.get_table_names():
            return False
        return _alembic_current_revision() is None
    except Exception:
        return False


def _is_already_applied_schema_error(exc: BaseException) -> bool:
    from sqlalchemy.exc import ProgrammingError

    if isinstance(exc, ProgrammingError):
        message = str(getattr(exc, "orig", exc)).lower()
        return any(
            token in message
            for token in (
                "already exists",
                "duplicate table",
                "duplicate column",
            )
        )
    return False


def _alembic_config():
    from alembic.config import Config

    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
    return cfg


def run_migrations() -> None:
    """Apply cloud Alembic migrations; fallback to metadata create_all only in development."""
    from alembic import command

    cfg = _alembic_config()
    try:
        if _database_pre_alembic():
            log.warning("Pre-Alembic database detected; stamping head before upgrade")
            command.stamp(cfg, "head")
        command.upgrade(cfg, "head")
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as exc:
        if _is_already_applied_schema_error(exc):
            try:
                if "users" in inspect(engine).get_table_names():
                    log.warning("Alembic upgrade conflict with existing schema; stamping head")
                    command.stamp(cfg, "head")
                    Base.metadata.create_all(bind=engine, checkfirst=True)
                    return
            except Exception:
                pass
        log.exception("Alembic upgrade failed")
        if is_production():
            raise
        log.warning("Falling back to Base.metadata.create_all()")
        Base.metadata.create_all(bind=engine)


