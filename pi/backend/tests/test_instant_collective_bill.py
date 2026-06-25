"""Pi instant collective bill and fiscal VAT."""

import json

import pytest
from app.fiscal_vat import split_gross_cents
from app.instant_collective_bill import ensure_instant_collective_bill
from app.models import CollectiveBill, SyncedBundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


def test_split_gross_cents_zero_rate():
    gross, net, vat = split_gross_cents(500, 0)
    assert gross == net == 500
    assert vat == 0


def test_ensure_instant_collective_bill(db_session):
    ev = {
        "id": 1,
        "payment_mode": "instant",
        "instant_collective_bill_uuid": "cb-instant-1",
        "instant_collective_bill_name": "Veranstalter",
    }
    bill = ensure_instant_collective_bill(db_session, ev)
    assert bill is not None
    assert bill.uuid == "cb-instant-1"
    assert bill.name == "Veranstalter"
    again = ensure_instant_collective_bill(db_session, ev)
    assert again.id == bill.id


def test_instant_order_assigns_collective_bill(api_context):
    client = api_context.client
    bundle = {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "currency": "CHF",
                "payment_mode": "instant",
                "instant_collective_bill_uuid": "cb-instant-1",
                "instant_collective_bill_name": "Veranstalter",
                "payment_types": ["cash"],
                "articles": {
                    "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
                },
                "configuration": {"stations": [], "event_waiters": [{"uuid": "w-1", "name": "Anna"}]},
            }
        ],
    }
    db = api_context.Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/orders",
        json={
            "client_order_id": "pwa-test-instant-001",
            "event_id": 1,
            "table_number": 5,
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": 1, "note": "", "additions": []}],
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("payment_status") == "paid"

    db = api_context.Session()
    try:
        from app.models import LocalOrder

        order = db.query(LocalOrder).filter(LocalOrder.client_order_id == "pwa-test-instant-001").first()
        assert order is not None
        assert order.collective_bill_id is not None
        payload = json.loads(order.payload_json)
        assert payload.get("collective_bill_uuid") == "cb-instant-1"
        assert payload.get("payments") == []
        bill = db.query(CollectiveBill).filter(CollectiveBill.uuid == "cb-instant-1").first()
        assert bill is not None
    finally:
        db.close()


def test_instant_order_rejects_invalid_payment_type(api_context):
    client = api_context.client
    bundle = {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "currency": "CHF",
                "payment_mode": "instant",
                "instant_collective_bill_uuid": "cb-instant-1",
                "instant_collective_bill_name": "Veranstalter",
                "payment_types": ["cash"],
                "articles": {
                    "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
                },
                "configuration": {"stations": [], "event_waiters": [{"uuid": "w-1", "name": "Anna"}]},
            }
        ],
    }
    db = api_context.Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/orders",
        json={
            "client_order_id": "pwa-test-instant-invalid-pay-001",
            "event_id": 1,
            "table_number": 5,
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": 1, "note": "", "additions": []}],
            "payments": [{"type": "card", "amount_cents": 500}],
        },
    )
    assert r.status_code == 400, r.text
    assert "not allowed" in r.json()["detail"]
