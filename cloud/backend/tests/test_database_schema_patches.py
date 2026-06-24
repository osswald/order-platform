"""Schema patch behaviour for legacy production drift."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.database import SessionLocal, apply_schema_patches, engine
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
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
    now = datetime.now(timezone.utc)
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
