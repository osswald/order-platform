"""Event create/update and tenant isolation."""

from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.main import app
from app.models import Event, HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _utc_now():
    return datetime.now(UTC)


def _setup_two_tenants():
    db = SessionLocal()
    try:
        hc_a = HireCompany(name="Events Tenant A")
        hc_b = HireCompany(name="Events Tenant B")
        db.add_all([hc_a, hc_b])
        db.flush()
        org_a = Organisation(name="Org A", country_id=country_id_by_code(db, "CH"), hire_company_id=hc_a.id, currency="CHF")
        org_b = Organisation(name="Org B", country_id=country_id_by_code(db, "CH"), hire_company_id=hc_b.id, currency="CHF")
        db.add_all([org_a, org_b])
        db.flush()
        db.add(
            User(
                email="events-a@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc_a.id,
            )
        )
        db.commit()
        return org_a.id, org_b.id
    finally:
        db.close()


def _token(email: str = "events-a@test.local") -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_create_event_and_status_transition():
    org_a_id, _ = _setup_two_tenants()
    headers = {"Authorization": f"Bearer {_token()}"}
    now = _utc_now()
    created = client.post(
        "/events/",
        headers=headers,
        json={
            "name": "Summer Fest",
            "status": "config",
            "start": (now + timedelta(days=1)).isoformat(),
            "end": (now + timedelta(days=2)).isoformat(),
            "organisation_id": org_a_id,
            "payment_mode": "pay_later",
            "payment_types": ["cash"],
        },
    )
    assert created.status_code == 200, created.text
    event_id = created.json()["id"]
    assert created.json()["status"] == "config"

    updated = client.put(
        f"/events/{event_id}",
        headers=headers,
        json={"status": "test"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "test"


def test_create_organisation_with_currency():
    _setup_two_tenants()
    db = SessionLocal()
    try:
        ch_id = country_id_by_code(db, "CH")
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {_token()}"}
    created = client.post(
        "/organisations/",
        headers=headers,
        json={
            "name": "CHF Org",
            "country_id": ch_id,
            "currency": "chf",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["currency"] == "CHF"


def test_org_admin_cannot_read_other_tenant_event():
    org_a_id, org_b_id = _setup_two_tenants()
    db = SessionLocal()
    try:
        now = _utc_now()
        ev = Event(
            name="Secret B",
            status="config",
            start=now,
            end=now + timedelta(hours=2),
            organisation_id=org_b_id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(ev)
        db.commit()
        event_b_id = ev.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {_token()}"}
    blocked = client.get(f"/events/{event_b_id}", headers=headers)
    assert blocked.status_code == 404

    listed = client.get("/events/", headers=headers)
    assert listed.status_code == 200
    assert all(e["organisation_id"] == org_a_id for e in listed.json())


def test_create_event_with_invalid_org_receipt_config():
    org_a_id, _ = _setup_two_tenants()
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_a_id).first()
        org.receipt_printing_config = {
            "station_receipt": {"size_table_or_pickup": "huge"},
        }
        db.commit()
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {_token()}"}
    now = _utc_now()
    created = client.post(
        "/events/",
        headers=headers,
        json={
            "name": "ZVV Schurter",
            "status": "config",
            "start": (now + timedelta(days=1)).isoformat(),
            "end": (now + timedelta(days=4)).isoformat(),
            "organisation_id": org_a_id,
            "payment_mode": "instant",
            "payment_types": ["cash"],
            "instant_collective_bill_name": "ZVV Schurter",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["name"] == "ZVV Schurter"
    assert created.json()["payment_mode"] == "instant"
