"""Cash drawer auto-kick on register cash payments."""

import json
import uuid

import pytest
from app.escpos_render import build_cash_drawer_kick
from app.models import OutboxEntry, PrintJob
from tests.fixtures_bundles import bundle_copy, cash_register_bundle, payment_receipts_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    b = bundle_copy(cash_register_bundle())
    b["events"][0]["configuration"]["cash_registers"][0]["cash_drawer_command"] = "escp_pin2"
    return b


@pytest.fixture
def client(client_session):
    return client_session


def _register_cash_order(c, *, payments=None, amount_cents=500):
    if payments is None:
        payments = [{"type": "cash", "amount_cents": amount_cents}]
    return c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": None,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [{"article_id": 20, "qty": 1, "note": "", "additions": []}],
            "payments": payments,
        },
    )


def test_register_cash_payment_enqueues_drawer_print_job_and_sync(client):
    c, Session = client
    r = _register_cash_order(c)
    assert r.status_code == 200, r.text

    db = Session()
    try:
        jobs = db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").all()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.station_uuid == "reg-1"
        assert job.printer_host == "127.0.0.1"

        outbox = db.query(OutboxEntry).filter(OutboxEntry.entity_type == "cash_drawer").all()
        assert len(outbox) == 1
        payload = json.loads(outbox[0].payload_json)
        assert payload["cash_register_uuid"] == "reg-1"
        assert payload["cash_register_name"] == "Hauptkasse"
        assert payload["cash_drawer_command"] == "escp_pin2"
        assert payload["payment_id"] is not None
    finally:
        db.close()


def test_no_drawer_job_when_command_none(client, bundle):
    c, Session = client
    bundle["events"][0]["configuration"]["cash_registers"][0]["cash_drawer_command"] = "none"
    from app.models import SyncedBundle

    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).one()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()

    r = _register_cash_order(c)
    assert r.status_code == 200, r.text

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() == 0
        assert db.query(OutboxEntry).filter(OutboxEntry.entity_type == "cash_drawer").count() == 0
    finally:
        db.close()


def test_waiter_cash_pay_does_not_open_drawer(client):
    c, Session = client
    from tests.fixtures_bundles import bundle_copy

    waiter_bundle = bundle_copy(payment_receipts_bundle())
    from app.models import SyncedBundle

    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).one()
        row.json_body = json.dumps(waiter_bundle)
        db.commit()
    finally:
        db.close()

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

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() == 0
        assert db.query(OutboxEntry).filter(OutboxEntry.entity_type == "cash_drawer").count() == 0
    finally:
        db.close()


def test_split_payment_with_cash_opens_drawer(client):
    c, Session = client
    r = _register_cash_order(
        c,
        payments=[
            {"type": "cash", "amount_cents": 300},
            {"type": "cash", "amount_cents": 200},
        ],
        amount_cents=500,
    )
    assert r.status_code == 200, r.text

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() == 1
        outbox = db.query(OutboxEntry).filter(OutboxEntry.entity_type == "cash_drawer").one()
        payload = json.loads(outbox.payload_json)
        cash_parts = [p for p in payload.get("payments") or [] if p.get("type") == "cash"]
        assert cash_parts and int(cash_parts[0]["amount_cents"]) == 300
    finally:
        db.close()


def test_drawer_job_payload_matches_preset(client):
    c, Session = client
    r = _register_cash_order(c)
    assert r.status_code == 200, r.text

    db = Session()
    try:
        import base64

        job = db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").one()
        raw = base64.b64decode(job.escpos_payload)
        assert raw == build_cash_drawer_kick("escp_pin2")
    finally:
        db.close()
