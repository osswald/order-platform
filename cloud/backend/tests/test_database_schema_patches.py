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


def test_apply_schema_patches_drops_legacy_event_currency_column():
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE events ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'CHF'")
        )

    apply_schema_patches()

    inspector_cols = {c["name"] for c in inspect(engine).get_columns("events")}
    assert "currency" not in inspector_cols


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

    assert _alembic_current_revision() == "005_stripe_webhook_events"
    inspector = inspect(engine)
    assert "stripe_webhook_events" in inspector.get_table_names()


def test_run_migrations_applies_fresh_database_from_scratch():
    from app.database import Base, _alembic_current_revision, run_migrations

    Base.metadata.drop_all(bind=engine)

    run_migrations()

    assert _alembic_current_revision() == "005_stripe_webhook_events"
    assert "users" in inspect(engine).get_table_names()
