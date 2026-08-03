"""Schema patch behaviour for legacy production drift."""

from datetime import UTC, datetime, timedelta

import pytest
from app.database import SessionLocal, apply_schema_patches, engine
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from tests.helpers import country_id_by_code

client = TestClient(app)


def test_patch_edge_order_items_ordered_at_adds_column():
    from app.database import _patch_edge_order_items_ordered_at

    _patch_edge_order_items_ordered_at()

    cols = {c["name"] for c in inspect(engine).get_columns("edge_order_items")}
    assert "ordered_at" in cols


def test_apply_schema_patches_drops_legacy_event_currency_column():
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE events ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'CHF'")
        )

    apply_schema_patches()

    inspector_cols = {c["name"] for c in inspect(engine).get_columns("events")}
    assert "currency" not in inspector_cols


def test_apply_schema_patches_does_not_readd_legacy_income_account(monkeypatch):
    """Regression: re-adding then dropping income_account each boot burns PG's 1600-col limit."""
    import app.database as database

    added: list[tuple[str, str]] = []
    real_add = database._add_column_if_missing

    def _spy(table: str, column: str, ddl_sqlite: str, ddl_other: str) -> None:
        added.append((table, column))
        real_add(table, column, ddl_sqlite, ddl_other)

    monkeypatch.setattr(database, "_add_column_if_missing", _spy)
    apply_schema_patches()

    assert ("articles", "income_account") not in added
    cols = {c["name"] for c in inspect(engine).get_columns("articles")}
    assert "income_account" not in cols
    assert "accounting_account_id" in cols


def test_apply_schema_patches_drops_legacy_income_account():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE articles ADD COLUMN income_account INTEGER"))

    apply_schema_patches()
    cols = {c["name"] for c in inspect(engine).get_columns("articles")}
    assert "income_account" not in cols
    assert "accounting_account_id" in cols

    apply_schema_patches()
    cols = {c["name"] for c in inspect(engine).get_columns("articles")}
    assert "income_account" not in cols


def test_create_event_after_legacy_currency_column_removed():
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE events ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'CHF'")
        )
    apply_schema_patches()

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        hc = HireCompany(name="Patch Tenant")
        db.add(hc)
        db.flush()
        ch_id = country_id_by_code(db, "CH")
        org = Organisation(
            name="Patch Org",
            country_id=ch_id,
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="patch@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        org_id = org.id
    finally:
        db.close()

    token = client.post("/auth/token", data={"username": "patch@test.local", "password": "secret"})
    assert token.status_code == 200, token.text
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    now = datetime.now(UTC)
    created = client.post(
        "/events/",
        headers=headers,
        json={
            "name": "ZVV Schurter",
            "status": "config",
            "start": (now + timedelta(days=1)).isoformat(),
            "end": (now + timedelta(days=4)).isoformat(),
            "organisation_id": org_id,
            "payment_mode": "instant",
            "payment_types": ["cash"],
            "instant_collective_bill_name": "ZVV Schurter",
        },
    )
    assert created.status_code == 200, created.text


def test_patch_tenant_admin_role_renames_org_admin():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Role Patch HC")
        db.add(hc)
        db.flush()
        db.add(
            User(
                email="orgadmin@test.local",
                hashed_password=get_password_hash("secret"),
                role="org_admin",
                hire_company_id=hc.id,
            )
        )
        db.commit()
    finally:
        db.close()

    from app.database import _patch_tenant_admin_role

    _patch_tenant_admin_role()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "orgadmin@test.local").one()
        assert user.role == ROLE_TENANT_ADMIN
    finally:
        db.close()


def test_seed_countries_is_idempotent():
    from app.database import _seed_countries
    from app.models import Country

    _seed_countries()
    db = SessionLocal()
    try:
        first_count = db.query(Country).count()
        assert first_count > 0
    finally:
        db.close()

    _seed_countries()
    db = SessionLocal()
    try:
        second_count = db.query(Country).count()
        assert second_count == first_count
    finally:
        db.close()


def test_patch_hire_companies_tenancy_creates_default_verleiher():
    from app.database import _patch_hire_companies_tenancy
    from app.models import HireCompany
    from app.roles import DEFAULT_HIRE_COMPANY_NAME

    _patch_hire_companies_tenancy()

    db = SessionLocal()
    try:
        default_hc = (
            db.query(HireCompany).filter(HireCompany.name == DEFAULT_HIRE_COMPANY_NAME).first()
        )
        assert default_hc is not None
        orgs_without_hc = (
            db.query(Organisation).filter(Organisation.hire_company_id.is_(None)).count()
        )
        assert orgs_without_hc == 0
    finally:
        db.close()


def test_seed_payment_types_and_tax_codes_populate_reference_data():
    from app.database import _seed_payment_types, _seed_tax_codes
    from app.models import PaymentType, TaxCode

    _seed_payment_types()
    _seed_tax_codes()

    db = SessionLocal()
    try:
        assert db.query(PaymentType).filter(PaymentType.slug == "cash").first() is not None
        assert db.query(TaxCode).count() > 0
    finally:
        db.close()

    _seed_payment_types()
    _seed_tax_codes()
    db = SessionLocal()
    try:
        cash_count = db.query(PaymentType).filter(PaymentType.slug == "cash").count()
        tax_count = db.query(TaxCode).count()
    finally:
        db.close()

    _seed_payment_types()
    _seed_tax_codes()
    db = SessionLocal()
    try:
        assert db.query(PaymentType).filter(PaymentType.slug == "cash").count() == cash_count
        assert db.query(TaxCode).count() == tax_count
    finally:
        db.close()


def test_run_migrations_reraises_in_production(monkeypatch):
    import alembic.command as alembic_command

    monkeypatch.setattr("app.database.is_production", lambda: True)
    monkeypatch.setattr("app.database._database_pre_alembic", lambda: False)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("alembic upgrade failed")

    monkeypatch.setattr(alembic_command, "upgrade", _boom)

    from app.database import run_migrations

    with pytest.raises(RuntimeError, match="alembic upgrade failed"):
        run_migrations()


def test_run_migrations_bootstraps_pre_alembic_database():
    from app.database import Base, _alembic_current_revision, run_migrations
    from app.models import EdgeOrderSession

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine, tables=[User.__table__])
    EdgeOrderSession.__table__.create(bind=engine, checkfirst=True)

    run_migrations()

    assert _alembic_current_revision() == "011_edge_submitted_order_collective_bill_uuid"
    inspector = inspect(engine)
    assert "stripe_webhook_events" in inspector.get_table_names()


def test_run_migrations_applies_fresh_database_from_scratch():
    from app.database import Base, _alembic_current_revision, run_migrations

    Base.metadata.drop_all(bind=engine)

    run_migrations()

    assert _alembic_current_revision() == "011_edge_submitted_order_collective_bill_uuid"
    assert "users" in inspect(engine).get_table_names()


def test_alembic_revision_ids_fit_version_num_column():
    """Alembic's default version_num is VARCHAR(32); we widen to 64 — keep ids within that."""
    from pathlib import Path

    from app.database import ALEMBIC_VERSION_NUM_MAX_LEN

    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    too_long: list[str] = []
    for path in sorted(versions_dir.glob("*.py")):
        namespace: dict[str, object] = {}
        exec(path.read_text(encoding="utf-8"), namespace)
        revision = namespace.get("revision")
        if not isinstance(revision, str):
            continue
        if len(revision) > ALEMBIC_VERSION_NUM_MAX_LEN:
            too_long.append(f"{path.name}: {revision!r} ({len(revision)})")
    assert not too_long, "revision id(s) exceed alembic_version.version_num capacity:\n" + "\n".join(
        too_long
    )


def test_ensure_alembic_version_num_capacity_stores_long_revision():
    from app.database import (
        ALEMBIC_VERSION_NUM_MAX_LEN,
        _ensure_alembic_version_num_capacity,
    )

    long_rev = "008_edge_credential_reported_app_version"
    assert len(long_rev) > 32
    assert len(long_rev) <= ALEMBIC_VERSION_NUM_MAX_LEN

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    _ensure_alembic_version_num_capacity()

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
            {"v": long_rev},
        )
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    assert row is not None
    assert row[0] == long_rev


def test_ensure_alembic_version_num_capacity_widens_existing_narrow_column(monkeypatch):
    """Postgres path must ALTER a legacy VARCHAR(32) version_num before long revision ids."""
    from app.database import _ensure_alembic_version_num_capacity

    executed: list[str] = []

    class _FakeDialect:
        name = "postgresql"

    class _FakeResult:
        def fetchone(self):
            return ("32",)

    class _FakeConn:
        def execute(self, stmt, *args, **kwargs):
            executed.append(str(stmt))
            sql = str(stmt).lower()
            if "character_maximum_length" in sql or "information_schema" in sql:
                return _FakeResult()
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _FakeEngine:
        dialect = _FakeDialect()

        def begin(self):
            return _FakeConn()

    monkeypatch.setattr("app.database.engine", _FakeEngine())
    monkeypatch.setattr(
        "app.database.inspect",
        lambda _engine: type("I", (), {"get_table_names": lambda self: ["alembic_version"]})(),
    )

    _ensure_alembic_version_num_capacity()

    assert any("ALTER TABLE alembic_version" in s and "VARCHAR(64)" in s for s in executed)


def test_run_migrations_ensures_version_num_capacity_before_upgrade(monkeypatch):
    import alembic.command as alembic_command
    from app.database import run_migrations

    calls: list[str] = []

    monkeypatch.setattr("app.database._database_pre_alembic", lambda: False)
    monkeypatch.setattr(
        "app.database._ensure_alembic_version_num_capacity",
        lambda: calls.append("ensure"),
    )
    monkeypatch.setattr(
        alembic_command,
        "upgrade",
        lambda *_a, **_k: calls.append("upgrade"),
    )
    monkeypatch.setattr(
        "app.database.Base.metadata.create_all",
        lambda **_k: calls.append("create_all"),
    )

    run_migrations()

    assert calls[:2] == ["ensure", "upgrade"]
