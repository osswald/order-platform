"""Order and line discount pricing and API validation."""

import uuid

import pytest
from app.pricing import (
    apply_discount_cents,
    line_gross_cents,
    line_total_cents,
    order_subtotal_cents,
    order_total_cents,
)
from tests.fixtures_bundles import bundle_copy, default_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


def discounts_bundle():
    bundle = default_bundle()
    bundle["events"][0]["discounts_enabled"] = True
    bundle["events"][0]["articles"]["11"] = {"id": 11, "name": "Wein", "price": 10.0, "additions": []}
    return bundle


def test_apply_discount_percent_and_amount():
    assert apply_discount_cents(1000, {"kind": "percent", "value": 10}) == 900
    assert apply_discount_cents(1000, {"kind": "amount", "value": 250}) == 750
    assert apply_discount_cents(100, {"kind": "amount", "value": 500}) == 0


def test_line_and_order_totals():
    arts = {"10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []}}
    ev = {"discounts_enabled": True}
    lines = [
        {"article_id": 10, "qty": 2, "discount": {"kind": "percent", "value": 10}},
        {"article_id": 10, "qty": 1},
    ]
    assert line_gross_cents(lines[0], arts) == 1000
    assert line_total_cents(lines[0], arts) == 900
    assert order_subtotal_cents(lines, ev, arts) == 1400
    assert order_total_cents(lines, {"kind": "amount", "value": 200}, ev, arts) == 1200


def _seed_discounts_bundle(Session):
    import json

    from app.models import SyncedBundle

    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        if row:
            row.json_body = json.dumps(bundle_copy(discounts_bundle()))
        else:
            db.add(SyncedBundle(id=1, json_body=json.dumps(bundle_copy(discounts_bundle()))))
        db.commit()
    finally:
        db.close()


def test_order_submit_with_discounts(client_session):
    c, Session = client_session
    _seed_discounts_bundle(Session)
    client_order_id = f"pwa-{uuid.uuid4().hex[:12]}"
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": client_order_id,
            "event_id": 1,
            "table_number": 2,
            "lines": [
                {
                    "article_id": 10,
                    "qty": 2,
                    "station_uuid": None,
                    "note": "",
                    "additions": [],
                    "discount": {"kind": "percent", "value": 10},
                },
            ],
            "order_discount": {"kind": "amount", "value": 50},
        },
    )
    assert response.status_code == 200, response.text
    db = Session()
    try:
        from app.models import LocalOrder

        order = db.query(LocalOrder).filter(LocalOrder.client_order_id == client_order_id).one()
        import json

        payload = json.loads(order.payload_json)
        assert payload["order_discount"] == {"kind": "amount", "value": 50}
        assert payload["lines"][0]["discount"] == {"kind": "percent", "value": 10}
    finally:
        db.close()


def test_table_summary_line_groups_include_discount(client_session):
    c, Session = client_session
    _seed_discounts_bundle(Session)
    table_number = 42
    client_order_id = f"pwa-{uuid.uuid4().hex[:12]}"
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": client_order_id,
            "event_id": 1,
            "table_number": table_number,
            "lines": [
                {
                    "article_id": 10,
                    "qty": 2,
                    "station_uuid": None,
                    "note": "",
                    "additions": [],
                    "discount": {"kind": "percent", "value": 10},
                },
            ],
        },
    )
    assert response.status_code == 200, response.text

    summary = c.get(f"/v1/tables/{table_number}", params={"event_id": 1})
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data["total_cents"] == 900
    assert len(data["line_groups"]) == 1
    group = data["line_groups"][0]
    assert group["discount"] == {"kind": "percent", "value": 10}
    assert group["line_total_cents"] == 900
    assert group["unit_cents"] == 500
    assert group["total_qty"] == 2


def test_settle_partial_keeps_discount_on_receipt(client_session):
    import json

    from app.models import PaymentReceipt
    from app.print_worker import build_payment_receipt_text
    from tests.fixtures_bundles import default_bundle

    c, Session = client_session
    _seed_discounts_bundle(Session)
    table_number = 43
    client_order_id = f"pwa-{uuid.uuid4().hex[:12]}"
    order_res = c.post(
        "/v1/orders",
        json={
            "client_order_id": client_order_id,
            "event_id": 1,
            "table_number": table_number,
            "lines": [
                {
                    "article_id": 10,
                    "qty": 2,
                    "station_uuid": None,
                    "note": "",
                    "additions": [],
                    "discount": {"kind": "percent", "value": 10},
                },
            ],
        },
    )
    assert order_res.status_code == 200, order_res.text

    summary = c.get(f"/v1/tables/{table_number}", params={"event_id": 1})
    group = summary.json()["line_groups"][0]
    selection = {
        "article_id": 10,
        "qty": 2,
        "note": "",
        "additions": [],
        "discount": group["discount"],
    }
    settle = c.post(
        f"/v1/tables/{table_number}/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 900}],
            "selections": [selection],
        },
    )
    assert settle.status_code == 200, settle.text
    assert settle.json()["paid_cents"] == 900
    payment_id = settle.json()["payment_id"]
    assert payment_id is not None

    db = Session()
    try:
        receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == payment_id).one()
        payload = json.loads(receipt.payload_json)
        assert payload["lines"][0]["discount"] == {"kind": "percent", "value": 10}
    finally:
        db.close()

    ev = default_bundle()["events"][0]
    ev["discounts_enabled"] = True
    raw = build_payment_receipt_text(
        payload,
        ev.get("name", "Event"),
        articles=ev.get("articles"),
        currency=ev.get("currency", "CHF"),
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Rabatt 10%" in text


def test_order_submit_rejects_discounts_when_disabled(client_session):
    c, _ = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 2,
            "lines": [{"article_id": 10, "qty": 1, "discount": {"kind": "percent", "value": 5}}],
        },
    )
    assert response.status_code == 400
