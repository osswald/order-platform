"""Waiter order create flow."""

from tests.fixtures_bundles import bundle_copy, default_bundle


def test_create_waiter_order_pay_later(client_session):
    client, Session = client_session
    bundle = bundle_copy(default_bundle())
    ev = bundle["events"][0]
    ev["payment_mode"] = "pay_later"
    ev["articles"] = {
        "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
    }
    ev["configuration"] = {"stations": []}

    db = Session()
    try:
        import json

        from app.models import SyncedBundle

        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()

    client_order_id = "waiter-order-001"
    created = client.post(
        "/v1/orders",
        json={
            "client_order_id": client_order_id,
            "event_id": 1,
            "table_number": 5,
            "order_source": "waiter",
            "lines": [{"article_id": 10, "qty": 1, "note": ""}],
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["local_order_id"]
    assert body["payment_status"] == "open"

    duplicate = client.post(
        "/v1/orders",
        json={
            "client_order_id": client_order_id,
            "event_id": 1,
            "table_number": 5,
            "order_source": "waiter",
            "lines": [{"article_id": 10, "qty": 1, "note": ""}],
        },
    )
    assert duplicate.status_code == 409
