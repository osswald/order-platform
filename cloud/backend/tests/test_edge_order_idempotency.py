"""Edge order submission idempotency."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    EdgeSubmittedOrder,
    Event,
    HireCompany,
    Organisation,
)
from app.security import get_password_hash
from tests.helpers import country_id_by_code

client = TestClient(app)


def _edge_fixture() -> tuple[dict[str, str], int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Order HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Order Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        now = datetime.now(timezone.utc)
        ev = Event(
            name="Live",
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(days=1),
            organisation_id=org.id,
        )
        db.add(ev)
        db.flush()
        appliance = Appliance(hire_company_id=hc.id, type="server", name="Pi")
        db.add(appliance)
        db.flush()
        today = now.date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today,
                end_date=today,
                returned_at=None,
            )
        )
        secret = f"secret-{suffix}"
        cred = ApplianceEdgeCredential(
            appliance_id=appliance.id,
            edge_client_id=f"cid-{suffix}",
            edge_secret_hash=get_password_hash(secret),
            status="active",
        )
        db.add(cred)
        db.commit()
        return (
            {
                "X-Edge-Client-Id": cred.edge_client_id,
                "X-Edge-Secret": secret,
            },
            ev.id,
        )
    finally:
        db.close()


def test_edge_order_duplicate_returns_same_server_id():
    headers, event_id = _edge_fixture()
    client_order_id = f"order-{uuid4().hex}"
    payload = {
        "client_order_id": client_order_id,
        "event_id": event_id,
        "payload": {
            "client_order_id": client_order_id,
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
        },
    }
    first = client.post("/edge/v1/orders", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["duplicate"] is False
    assert first_body["server_order_id"]

    second = client.post("/edge/v1/orders", headers=headers, json=payload)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["duplicate"] is True
    assert second_body["server_order_id"] == first_body["server_order_id"]

    db = SessionLocal()
    try:
        count = (
            db.query(EdgeSubmittedOrder)
            .filter(EdgeSubmittedOrder.client_order_id == client_order_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()


def test_edge_order_concurrent_duplicate_requests():
    """Two sequential duplicate posts behave like concurrent idempotent retries."""
    headers, event_id = _edge_fixture()
    client_order_id = f"order-concurrent-{uuid4().hex}"
    payload = {
        "client_order_id": client_order_id,
        "event_id": event_id,
        "payload": {
            "client_order_id": client_order_id,
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
        },
    }
    results = [client.post("/edge/v1/orders", headers=headers, json=payload) for _ in range(3)]
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    server_ids = {r.json()["server_order_id"] for r in results}
    assert len(server_ids) == 1
    duplicates = sum(1 for r in results if r.json().get("duplicate"))
    assert duplicates == 2

    db = SessionLocal()
    try:
        count = (
            db.query(EdgeSubmittedOrder)
            .filter(EdgeSubmittedOrder.client_order_id == client_order_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()
