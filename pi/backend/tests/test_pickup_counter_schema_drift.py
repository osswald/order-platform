"""Schema drift: legacy event_pickup_counters without station_uuid.

Mirrors Pis stuck behind the 006 merge (cash_session_uuid only) where runtime
patches already added print_jobs.render_context_json / synced_bundle.etag, so
Alembic upgrade fails before 010_pickup_counter_station can run.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.database import Base, apply_pickup_counter_schema_patches, run_migrations
from app.routers.edge_common import _allocate_pickup_number
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _legacy_pickup_counter_engine():
    """DB shaped like pre-010: event_id PK only, plus columns already patched at runtime."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE event_pickup_counters (
                    event_id INTEGER NOT NULL PRIMARY KEY,
                    next_number INTEGER NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO event_pickup_counters (event_id, next_number) VALUES (13, 7)"
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE print_jobs (
                    id INTEGER PRIMARY KEY,
                    local_order_id INTEGER NOT NULL,
                    printer_host VARCHAR(255) NOT NULL,
                    printer_port INTEGER NOT NULL,
                    escpos_payload BLOB NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    render_context_json TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE synced_bundle (
                    id INTEGER PRIMARY KEY,
                    json_body TEXT NOT NULL,
                    updated_at DATETIME,
                    etag VARCHAR(128)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE local_stock_state (
                    id INTEGER PRIMARY KEY,
                    event_id INTEGER NOT NULL,
                    entity_kind VARCHAR(32) NOT NULL,
                    entity_id INTEGER NOT NULL,
                    in_stock FLOAT NOT NULL,
                    monitor_stock BOOLEAN NOT NULL,
                    sellable BOOLEAN NOT NULL
                )
                """
            )
        )
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('006_cash_session_uuid')")
        )
    return engine


def test_pickup_counter_schema_patch_adds_station_uuid_and_preserves_counts():
    import app.database as database

    engine = _legacy_pickup_counter_engine()
    database.engine = engine

    cols = {c["name"] for c in inspect(engine).get_columns("event_pickup_counters")}
    assert "station_uuid" not in cols

    apply_pickup_counter_schema_patches()

    cols = {c["name"] for c in inspect(engine).get_columns("event_pickup_counters")}
    assert cols >= {"event_id", "station_uuid", "next_number"}
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT event_id, station_uuid, next_number FROM event_pickup_counters")
        ).fetchall()
    assert rows == [(13, "", 7)]

    # Idempotent
    apply_pickup_counter_schema_patches()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT event_id, station_uuid, next_number FROM event_pickup_counters")
        ).fetchall()
    assert rows == [(13, "", 7)]


def test_allocate_works_after_pickup_counter_schema_patch():
    import app.database as database

    engine = _legacy_pickup_counter_engine()
    database.engine = engine
    apply_pickup_counter_schema_patches()

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        assert _allocate_pickup_number(db, 13) == 7
        assert _allocate_pickup_number(db, 13, station_uuid="st-kitchen") == 1
        db.commit()
    finally:
        db.close()


def test_run_migrations_unblocks_stuck_006_and_upgrades_pickup_counters():
    """Reproduce Pi drift: one 006 head stamped, sibling columns already present."""
    import app.database as database

    engine = _legacy_pickup_counter_engine()
    # Minimal tables so create_all / later migrations do not fail awkwardly.
    Base.metadata.create_all(bind=engine)
    database.engine = engine

    # Re-assert legacy pickup shape after create_all (ORM model has station_uuid —
    # create_all will not alter existing table).
    cols = {c["name"] for c in inspect(engine).get_columns("event_pickup_counters")}
    assert "station_uuid" not in cols

    run_migrations()

    cols = {c["name"] for c in inspect(engine).get_columns("event_pickup_counters")}
    assert "station_uuid" in cols

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
    assert current == head

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        assert _allocate_pickup_number(db, 13) == 7
        db.commit()
    finally:
        db.close()
