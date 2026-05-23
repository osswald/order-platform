"""Payment receipt ESC/POS endpoints for Android Bluetooth printing."""

import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import PaymentReceipt, SyncedBundle


@pytest.fixture
def client():
    import app.database as database

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    Session = database.SessionLocal
    db = Session()
    bundle = {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Receipt Test",
                "currency": "CHF",
                "payment_mode": "pay_now",
                "payment_types": ["cash"],
                "printer_hosts": {},
                "articles": {
                    "10": {"id": 10, "name": "Burger", "price": 12.0, "additions": []},
                },
                "configuration": {
                    "stations": [],
                    "event_waiters": [{"uuid": "w-1", "name": "Anna"}],
                },
            }
        ],
    }
    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()
    db.close()

    from app.routers import edge_api

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[edge_api.get_db] = override_get_db
    with TestClient(app) as c:
        yield c, Session
    app.dependency_overrides.clear()


def test_order_payment_creates_receipt_payload(client):
    c, Session = client
    order = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 7,
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": 1, "note": "", "additions": []}],
            "payments": [],
        },
    )
    assert order.status_code == 200, order.text
    order_id = order.json()["local_order_id"]

    paid = c.post(
        f"/v1/orders/{order_id}/pay",
        json={"payments": [{"type": "cash", "amount_cents": 1200}]},
    )
    assert paid.status_code == 200, paid.text
    payment_id = paid.json()["payment_id"]

    db = Session()
    try:
        receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == payment_id).one()
        payload = json.loads(receipt.payload_json)
        assert payload["waiter_name"] == "Anna"
        assert payload["table_number"] == 7
    finally:
        db.close()

    esc = c.post(f"/v1/payments/{payment_id}/receipt", json={"reprint": True})
    assert esc.status_code == 200, esc.text
    raw = base64.b64decode(esc.json()["escpos_payload"])
    assert b"Beleg" in raw
    assert "Receipt Test".encode() in raw
    assert b"Kopie" in raw

    listing = c.get("/v1/payments", params={"event_id": 1, "waiter_uuid": "w-1"})
    assert listing.status_code == 200, listing.text
    assert listing.json()["payments"][0]["payment_id"] == payment_id
    assert listing.json()["payments"][0]["total_cents"] == 1200


def test_backend_generates_test_receipt(client):
    c, _ = client
    response = c.post("/v1/printers/test-receipt", json={"event_id": 1})
    assert response.status_code == 200, response.text
    raw = base64.b64decode(response.json()["escpos_payload"])
    assert b"Beleg" in raw
    assert b"Testartikel" in raw
