"""Edge order submission idempotency."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
from fastapi.testclient import TestClient

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
        now = datetime.now(UTC)
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
    """Three sequential duplicate posts behave like idempotent retries."""
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


def test_edge_order_parallel_duplicate_requests():
    """Simultaneous duplicate POSTs must create only one server order row."""
    headers, event_id = _edge_fixture()
    client_order_id = f"order-parallel-{uuid4().hex}"
    payload = {
        "client_order_id": client_order_id,
        "event_id": event_id,
        "payload": {
            "client_order_id": client_order_id,
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
        },
    }

    def _submit():
        worker = TestClient(app)
        return worker.post("/edge/v1/orders", headers=headers, json=payload)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_submit) for _ in range(4)]
        results = [future.result() for future in as_completed(futures)]

    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    server_ids = {r.json()["server_order_id"] for r in results}
    assert len(server_ids) == 1
    assert sum(1 for r in results if r.json().get("duplicate")) >= 1

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


def test_operational_chunk_duplicate_returns_ack():
    headers, event_id = _edge_fixture()
    chunk_id = f"chunk-{uuid4().hex}"
    payload = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": "cash_session",
        "payload": {
            "entity_type": "cash_session",
            "session_uuid": str(uuid4()),
            "opened_at": datetime.now(UTC).isoformat(),
        },
    }
    first = client.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["accepted"] == 1

    second = client.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["accepted"] == 0

    db = SessionLocal()
    try:
        count = (
            db.query(EdgeSubmittedOrder)
            .filter(EdgeSubmittedOrder.client_order_id == chunk_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()


def test_operational_chunk_parallel_duplicate_requests():
    """Simultaneous duplicate chunk POSTs must create only one idempotency row."""
    headers, event_id = _edge_fixture()
    chunk_id = f"chunk-parallel-{uuid4().hex}"
    payload = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": "kitchen_tickets",
        "payload": {"entity_type": "kitchen_tickets", "tickets": []},
    }

    def _submit():
        worker = TestClient(app)
        return worker.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_submit) for _ in range(4)]
        results = [future.result() for future in as_completed(futures)]

    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    accepted = sum(1 for r in results if r.json().get("accepted") == 1)
    assert accepted == 1

    db = SessionLocal()
    try:
        count = (
            db.query(EdgeSubmittedOrder)
            .filter(EdgeSubmittedOrder.client_order_id == chunk_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()
