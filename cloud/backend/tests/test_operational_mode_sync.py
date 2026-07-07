"""Reject test-tagged operational sync after event enters production."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.database import SessionLocal
from app.event_status import payload_is_stale_test
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    EdgeOrderItem,
    EdgeSubmittedOrder,
    Event,
    HireCompany,
    Organisation,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _edge_fixture(*, event_status: str = "prod") -> tuple[dict[str, str], int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Mode HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Mode Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Live",
            status=event_status,
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


@pytest.mark.parametrize(
    ("event_status", "payload_mode", "expected"),
    [
        ("prod", "test", True),
        ("archive", "test", True),
        ("prod", "prod", False),
        ("test", "test", False),
        ("prod", "", False),
        ("prod", None, False),
    ],
)
def test_payload_is_stale_test(event_status, payload_mode, expected):
    event = Event(status=event_status)
    payload = {}
    if payload_mode is not None:
        payload["mode"] = payload_mode
    assert payload_is_stale_test(event, payload) is expected


def test_test_tagged_chunk_dropped_when_event_prod():
    headers, event_id = _edge_fixture(event_status="prod")
    chunk_id = f"chunk-test-{uuid4().hex}"
    payload = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": "submission",
        "payload": {
            "mode": "test",
            "client_order_id": "o-test-1",
            "payment_status": "paid",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
            "payments": [{"type": "cash", "amount_cents": 500}],
            "local_order_id": 1,
            "session_id": 1,
        },
    }
    response = client.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["accepted"] == 0

    db = SessionLocal()
    try:
        assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event_id).count() == 0
        assert db.query(EdgeOrderItem).filter(EdgeOrderItem.event_id == event_id).count() == 0
    finally:
        db.close()


def test_prod_tagged_chunk_accepted_when_event_prod():
    headers, event_id = _edge_fixture(event_status="prod")
    chunk_id = f"chunk-prod-{uuid4().hex}"
    payload = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": "submission",
        "payload": {
            "mode": "prod",
            "client_order_id": "o-prod-1",
            "payment_status": "paid",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
            "payments": [{"type": "cash", "amount_cents": 500}],
            "local_order_id": 2,
            "session_id": 2,
        },
    }
    response = client.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["accepted"] == 1

    db = SessionLocal()
    try:
        assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event_id).count() == 1
        assert db.query(EdgeOrderItem).filter(EdgeOrderItem.event_id == event_id).count() == 1
    finally:
        db.close()


def test_test_tagged_edge_order_dropped_when_event_prod():
    headers, event_id = _edge_fixture(event_status="prod")
    client_order_id = f"order-{uuid4().hex}"
    payload = {
        "client_order_id": client_order_id,
        "event_id": event_id,
        "payload": {
            "mode": "test",
            "client_order_id": client_order_id,
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
        },
    }
    response = client.post("/edge/v1/orders", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["server_order_id"] == 0
    assert response.json()["duplicate"] is False

    db = SessionLocal()
    try:
        assert (
            db.query(EdgeSubmittedOrder)
            .filter(EdgeSubmittedOrder.client_order_id == client_order_id)
            .count()
            == 0
        )
    finally:
        db.close()
