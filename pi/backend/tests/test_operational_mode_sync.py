"""Operational payload mode tagging for cloud sync."""

from tests.fixtures_bundles import bundle_copy, default_bundle


def test_outbox_payload_carries_event_mode(client_session):
    client, Session = client_session
    bundle = bundle_copy(default_bundle())
    ev = bundle["events"][0]
    ev["status"] = "test"
    ev["payment_mode"] = "pay_later"
    ev["articles"] = {
        "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
    }
    ev["configuration"] = {"stations": []}

    db = Session()
    try:
        import json

        from app.models import OutboxEntry, SyncedBundle

        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()

    created = client.post(
        "/v1/orders",
        json={
            "client_order_id": "waiter-order-mode-001",
            "event_id": 1,
            "table_number": 5,
            "order_source": "waiter",
            "lines": [{"article_id": 10, "qty": 1, "note": ""}],
        },
    )
    assert created.status_code == 200, created.text

    db = Session()
    try:
        import json

        from app.models import OutboxEntry

        outbox = db.query(OutboxEntry).filter(OutboxEntry.event_id == 1).all()
        assert outbox, "expected sync outbox entry"
        payload = json.loads(outbox[0].payload_json)
        assert payload.get("mode") == "test"
    finally:
        db.close()
