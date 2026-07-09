"""Payment receipt ESC/POS endpoints for Android Bluetooth printing."""

import base64
import json
import uuid

import pytest
from app.models import PaymentReceipt, PrintJob
from app.print_worker import _escpos_text, run_print_job_sync
from tests.fixtures_bundles import bundle_copy, payment_receipts_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    return bundle_copy(payment_receipts_bundle())


@pytest.fixture
def client(client_session):
    return client_session


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
    assert _escpos_text("Receipt Test") in raw
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


def test_payment_receipt_escpos_accepts_paper_width(client):
    c, payment_id, _order_id = _pay_order(client)
    esc = c.post(f"/v1/payments/{payment_id}/receipt", json={"reprint": True, "paper_width": "58mm"})
    assert esc.status_code == 200, esc.text
    assert esc.json().get("escpos_payload")


def test_payment_receipt_escpos_accepts_charset(client):
    c, payment_id, _order_id = _pay_order(client)
    esc = c.post(f"/v1/payments/{payment_id}/receipt", json={"reprint": True, "charset": "pc850"})
    assert esc.status_code == 200, esc.text
    raw = base64.b64decode(esc.json()["escpos_payload"])
    assert raw[4] == 2


def _pay_order(client):
    c, _ = client
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
    return c, paid.json()["payment_id"], order_id


def test_payment_receipt_print_to_station(client, mock_printer_tcp):
    c, Session = client
    c, payment_id, order_id = _pay_order(client)

    bad = c.post(
        f"/v1/payments/{payment_id}/receipt/print",
        json={"station_uuid": "unknown-station"},
    )
    assert bad.status_code == 422, bad.text

    printed = c.post(
        f"/v1/payments/{payment_id}/receipt/print",
        json={"station_uuid": "st-bar"},
    )
    assert printed.status_code == 200, printed.text
    job_id = printed.json()["print_job_id"]

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.status == "queued"
        assert job.station_uuid == "st-bar"
        assert job.local_order_id == order_id
        assert job.printer_host == "127.0.0.1"
    finally:
        db.close()

    db = Session()
    try:
        run_print_job_sync(db, job_id)
        db.commit()
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.status == "sent"
    finally:
        db.close()
    assert len(mock_printer_tcp) == 1
    assert mock_printer_tcp[0] == ("127.0.0.1", 9100)


def test_payment_receipt_print_unknown_payment(client):
    c, _ = client
    response = c.post(
        "/v1/payments/99999/receipt/print",
        json={"station_uuid": "st-bar"},
    )
    assert response.status_code == 404
