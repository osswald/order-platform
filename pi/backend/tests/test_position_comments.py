"""Position comment (line note) validation and printing."""

import json
import uuid

import pytest
from app.print_worker import _escpos_text, build_escpos_receipt_text, build_payment_receipt_text
from tests.fixtures_bundles import bundle_copy, default_bundle, position_comments_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


def _seed_bundle(Session, bundle: dict) -> None:
    from app.models import SyncedBundle

    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        body = json.dumps(bundle_copy(bundle))
        if row:
            row.json_body = body
        else:
            db.add(SyncedBundle(id=1, json_body=body))
        db.commit()
    finally:
        db.close()


def test_order_submit_rejects_note_when_comments_disabled(client_session):
    c, Session = client_session
    _seed_bundle(Session, default_bundle())
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 2,
            "lines": [{"article_id": 10, "qty": 1, "note": "warm", "additions": []}],
        },
    )
    assert response.status_code == 400
    assert "comment" in response.json()["detail"].lower()


def test_order_submit_accepts_note_when_comments_enabled(client_session):
    c, Session = client_session
    _seed_bundle(Session, position_comments_bundle())
    client_order_id = f"pwa-{uuid.uuid4().hex[:12]}"
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": client_order_id,
            "event_id": 1,
            "table_number": 2,
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": 1, "note": "  extra scharf  ", "additions": []}],
        },
    )
    assert response.status_code == 200, response.text
    db = Session()
    try:
        from app.models import LocalOrder

        order = db.query(LocalOrder).filter(LocalOrder.client_order_id == client_order_id).one()
        payload = json.loads(order.payload_json)
        assert payload["lines"][0]["note"] == "extra scharf"
    finally:
        db.close()


def test_station_slip_includes_note():
    slip = build_escpos_receipt_text(
        {
            "table_number": 7,
            "lines": [{"article_id": 10, "qty": 1, "article_name": "Bier", "note": "warm", "additions": []}],
        },
        "Event",
        articles={"10": {"id": 10, "name": "Bier", "price": 5.0}},
    )
    assert _escpos_text("warm") in slip


def test_payment_receipt_omits_line_note():
    raw = build_payment_receipt_text(
        {
            "lines": [{"article_id": 10, "qty": 1, "note": "warm", "additions": []}],
            "payments": [{"type": "cash", "amount_cents": 500}],
        },
        "Event",
        articles={"10": {"id": 10, "name": "Bier", "price": 5.0}},
        currency="CHF",
    )
    text = raw.decode("cp858", errors="replace")
    assert "Bier" in text
    assert "warm" not in text
