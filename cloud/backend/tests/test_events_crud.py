"""Event create/update and tenant isolation."""

from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    EdgeOrderItem,
    EdgePayment,
    EdgeSubmittedOrder,
    Event,
    EventCollectiveBill,
    HireCompany,
    Organisation,
    User,
)
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


def _seed_event_operational_data(db, *, event_id: int, organisation_id: int, appliance_id: int) -> None:
    db.add(
        Appliance(
            id=appliance_id,
            hire_company_id=db.query(Organisation).filter(Organisation.id == organisation_id).first().hire_company_id,
            type="pi",
            name="Pi",
        )
    )
    db.add(
        EdgeSubmittedOrder(
            client_order_id=f"order-{event_id}",
            appliance_id=appliance_id,
            organisation_id=organisation_id,
            event_id=event_id,
            payload={"lines": [{"article_id": 1, "qty": 1}]},
        )
    )
    db.add(
        EdgeOrderItem(
            organisation_id=organisation_id,
            appliance_id=appliance_id,
            event_id=event_id,
            session_id=1,
            submission_id=1,
            article_id=1,
            article_name="Test",
            quantity=1,
            unit_price_cents=100,
            line_total_cents=100,
            payment_status="paid",
            method="cash",
            payload={},
        )
    )
    db.add(
        EdgePayment(
            organisation_id=organisation_id,
            appliance_id=appliance_id,
            event_id=event_id,
            submission_id=1,
            method="cash",
            amount_cents=100,
            payload={"type": "cash", "amount_cents": 100},
        )
    )
    db.add(EventCollectiveBill(uuid=f"cb-{event_id}", event_id=event_id, name="Team", appliance_id=appliance_id))
    db.commit()


def test_status_test_to_prod_purges_all_operational_data():
    org_a_id, _ = _setup_two_tenants()
    headers = {"Authorization": f"Bearer {_token()}"}
    now = _utc_now()
    created = client.post(
        "/events/",
        headers=headers,
        json={
            "name": "Purge Fest",
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

    to_test = client.put(f"/events/{event_id}", headers=headers, json={"status": "test"})
    assert to_test.status_code == 200, to_test.text

    db = SessionLocal()
    try:
        _seed_event_operational_data(db, event_id=event_id, organisation_id=org_a_id, appliance_id=9001)
        assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event_id).count() == 1
        assert db.query(EdgeOrderItem).filter(EdgeOrderItem.event_id == event_id).count() == 1
    finally:
        db.close()

    to_prod = client.put(f"/events/{event_id}", headers=headers, json={"status": "prod"})
    assert to_prod.status_code == 200, to_prod.text
    assert to_prod.json()["status"] == "prod"

    db = SessionLocal()
    try:
        assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event_id).count() == 0
        assert db.query(EdgeOrderItem).filter(EdgeOrderItem.event_id == event_id).count() == 0
        assert db.query(EdgePayment).filter(EdgePayment.event_id == event_id).count() == 0
        assert db.query(EventCollectiveBill).filter(EventCollectiveBill.event_id == event_id).count() == 0
    finally:
        db.close()

    now = _utc_now()
    stats = client.get(
        f"/events/{event_id}/stats",
        headers=headers,
        params={
            "from": (now - timedelta(hours=1)).isoformat(),
            "to": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()["totals"]["distinct_orders_count"] == 0
    assert stats.json()["totals"]["line_cents"] == 0

    transactions = client.get(f"/events/{event_id}/transactions", headers=headers)
    assert transactions.status_code == 200, transactions.text
    assert transactions.json()["items"] == []
    assert transactions.json()["total"] == 0


def test_purge_operational_endpoint_clears_data_keeps_status():
    org_a_id, _ = _setup_two_tenants()
    headers = {"Authorization": f"Bearer {_token()}"}
    now = _utc_now()
    created = client.post(
        "/events/",
        headers=headers,
        json={
            "name": "Purge API Fest",
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

    to_test = client.put(f"/events/{event_id}", headers=headers, json={"status": "test"})
    assert to_test.status_code == 200, to_test.text

    db = SessionLocal()
    try:
        _seed_event_operational_data(db, event_id=event_id, organisation_id=org_a_id, appliance_id=9002)
        assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event_id).count() == 1
    finally:
        db.close()

    purged = client.post(f"/events/{event_id}/purge-operational", headers=headers)
    assert purged.status_code == 200, purged.text
    assert purged.json()["ok"] is True
    assert purged.json()["status"] == "test"

    db = SessionLocal()
    try:
        assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event_id).count() == 0
        assert db.query(EdgeOrderItem).filter(EdgeOrderItem.event_id == event_id).count() == 0
        event = db.query(Event).filter(Event.id == event_id).one()
        assert event.status == "test"
    finally:
        db.close()


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
