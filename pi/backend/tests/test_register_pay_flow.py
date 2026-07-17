"""Register order-then-pay flow: open creation, order-scoped settle, collective assign."""

import json
import uuid

import pytest
from app.models import CollectiveBill, LocalOrder, OutboxEntry, PaymentReceipt, PrintJob
from tests.fixtures_bundles import bundle_copy, cash_register_bundle, voucher_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    b = bundle_copy(cash_register_bundle())
    b["events"][0]["configuration"]["cash_registers"][0]["cash_drawer_command"] = "escp_pin2"
    return b


@pytest.fixture
def client(client_session):
    return client_session


def _swap_bundle(Session, new_bundle):
    from app.models import SyncedBundle

    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).one()
        row.json_body = json.dumps(new_bundle)
        db.commit()
    finally:
        db.close()


def _register_order(c, *, lines=None, payments=None, voucher_redemptions=None):
    body = {
        "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
        "event_id": 1,
        "table_number": None,
        "order_source": "cash_register",
        "cash_register_uuid": "reg-1",
        "lines": lines or [{"article_id": 20, "qty": 1, "note": "", "additions": []}],
        "payments": payments or [],
    }
    if voucher_redemptions is not None:
        body["voucher_redemptions"] = voucher_redemptions
    return c.post("/v1/orders", json=body)


def _settle(c, order_id, *, selections, payments, voucher_redemptions=None):
    return c.post(
        f"/v1/orders/{order_id}/settle-partial",
        json={
            "event_id": 1,
            "payments": payments,
            "selections": selections,
            "voucher_redemptions": voucher_redemptions or [],
        },
    )


def _sel(article_id, qty, note="", additions=None):
    return {"article_id": article_id, "note": note, "qty": qty, "additions": additions or []}


# --- Open creation ---


def test_register_order_without_payments_created_open(client):
    c, Session = client
    r = _register_order(c)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "open"
    assert body["payment_id"] is None
    assert body["pickup_code"] == "A1"
    assert body["pickup_status"] == "ready"
    assert len(body["customer_print_job_ids"]) == 1
    assert len(body["print_job_ids"]) == 1

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.id == body["local_order_id"]).one()
        assert order.payment_status == "open"
        payload = json.loads(order.payload_json)
        assert payload["payment_status"] == "open"
        assert payload["payments"] == []
        assert payload["item_count"] == 1
        assert db.query(PaymentReceipt).count() == 0
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() == 0
    finally:
        db.close()


def test_register_order_with_payments_still_paid_at_create(client):
    c, Session = client
    r = _register_order(c, payments=[{"type": "cash", "amount_cents": 500}])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "paid"
    assert body["payment_id"] is not None


def test_register_order_wrong_amount_still_rejected(client):
    c, _ = client
    r = _register_order(c, payments=[{"type": "cash", "amount_cents": 100}])
    assert r.status_code == 400


def test_open_register_order_kitchen_flow_unchanged(client):
    c, _ = client
    r = _register_order(c, lines=[{"article_id": 10, "qty": 1, "note": "", "additions": []}])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "open"
    assert body["pickup_status"] == "pending"
    assert len(body["kitchen_ticket_ids"]) == 1

    kitchen = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    ticket = kitchen.json()["orders"][0]
    done = c.post(f"/v1/kitchen/tickets/{ticket['id']}/print")
    assert done.status_code == 200, done.text

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.json()["orders"][0]["pickup_status"] == "ready"


# --- Order summary ---


def test_order_summary(client):
    c, _ = client
    r = _register_order(c, lines=[{"article_id": 20, "qty": 2, "note": "", "additions": []}])
    oid = r.json()["local_order_id"]

    summary = c.get(f"/v1/orders/{oid}/summary")
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data["total_cents"] == 1000
    assert data["item_count"] == 2
    assert len(data["line_groups"]) == 1
    assert data["line_groups"][0]["article_id"] == 20
    assert data["line_groups"][0]["total_qty"] == 2

    settle = _settle(c, oid, selections=[_sel(20, 2)], payments=[{"type": "cash", "amount_cents": 1000}])
    assert settle.status_code == 200, settle.text
    assert c.get(f"/v1/orders/{oid}/summary").status_code == 404
    assert c.get("/v1/orders/999999/summary").status_code == 404


# --- Settlement ---


def test_order_settle_full_marks_order_paid_in_place(client):
    c, Session = client
    r = _register_order(c, lines=[{"article_id": 20, "qty": 2, "note": "", "additions": []}])
    oid = r.json()["local_order_id"]

    settle = _settle(c, oid, selections=[_sel(20, 2)], payments=[{"type": "cash", "amount_cents": 1000}])
    assert settle.status_code == 200, settle.text
    data = settle.json()
    assert data["paid_cents"] == 1000
    assert data["remaining_cents"] == 0
    assert data["payment_id"] is not None
    assert data["paid_order_ids"] == [oid]

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        assert order.payment_status == "paid"
        payload = json.loads(order.payload_json)
        assert payload["payment_status"] == "paid"
        assert payload["payments"][0]["amount_cents"] == 1000
        assert len(payload["lines"]) == 1  # lines stay on the order
        receipt = db.query(PaymentReceipt).filter(PaymentReceipt.id == data["payment_id"]).one()
        rp = json.loads(receipt.payload_json)
        assert rp["cash_register_uuid"] == "reg-1"
        assert rp["pickup_code"] == "A1"
    finally:
        db.close()


def test_order_settle_partial_split(client):
    c, Session = client
    r = _register_order(c, lines=[{"article_id": 20, "qty": 2, "note": "", "additions": []}])
    oid = r.json()["local_order_id"]

    first = _settle(c, oid, selections=[_sel(20, 1)], payments=[{"type": "cash", "amount_cents": 500}])
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["paid_cents"] == 500
    assert data["remaining_cents"] == 500
    assert data["paid_order_ids"] and data["paid_order_ids"] != [oid]

    db = Session()
    try:
        original = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        assert original.payment_status == "open"
        assert original.pickup_code == "A1"
        payload = json.loads(original.payload_json)
        assert payload["lines"][0]["qty"] == 1
        paid_order = db.query(LocalOrder).filter(LocalOrder.id == data["paid_order_ids"][0]).one()
        assert paid_order.payment_status == "paid"
        assert paid_order.pickup_status is None
        paid_payload = json.loads(paid_order.payload_json)
        assert paid_payload["order_source"] == "cash_register"
        assert paid_payload["cash_register_uuid"] == "reg-1"
    finally:
        db.close()

    # Pickup screen still shows exactly the original order with the full item count.
    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    orders = pickup.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["local_order_id"] == oid
    assert orders[0]["item_count"] == 2

    second = _settle(c, oid, selections=[_sel(20, 1)], payments=[{"type": "cash", "amount_cents": 500}])
    assert second.status_code == 200, second.text
    assert second.json()["remaining_cents"] == 0

    db = Session()
    try:
        original = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        assert original.payment_status == "paid"
    finally:
        db.close()


def test_order_settle_cash_kicks_drawer_at_settle_not_create(client):
    c, Session = client
    r = _register_order(c)
    oid = r.json()["local_order_id"]

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() == 0
    finally:
        db.close()

    settle = _settle(c, oid, selections=[_sel(20, 1)], payments=[{"type": "cash", "amount_cents": 500}])
    assert settle.status_code == 200, settle.text

    db = Session()
    try:
        jobs = db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").all()
        assert len(jobs) == 1
        assert jobs[0].station_uuid == "reg-1"
        outbox = db.query(OutboxEntry).filter(OutboxEntry.entity_type == "cash_drawer").all()
        assert len(outbox) == 1
        payload = json.loads(outbox[0].payload_json)
        assert payload["cash_register_uuid"] == "reg-1"
    finally:
        db.close()


def test_order_settle_amount_mismatch_rejected(client):
    c, _ = client
    r = _register_order(c)
    oid = r.json()["local_order_id"]
    settle = _settle(c, oid, selections=[_sel(20, 1)], payments=[{"type": "cash", "amount_cents": 400}])
    assert settle.status_code == 400


def test_order_settle_voucher_redemption(client):
    c, Session = client
    _swap_bundle(Session, bundle_copy(voucher_bundle()))

    r = _register_order(c, lines=[{"article_id": 20, "qty": 5, "note": "", "additions": []}])
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    settle = _settle(
        c,
        oid,
        selections=[_sel(20, 5)],
        payments=[{"type": "cash", "amount_cents": 500}],
        voucher_redemptions=[{"voucher_definition_uuid": "vd-20", "article_id": 0, "note": "", "qty": 1, "additions": []}],
    )
    assert settle.status_code == 200, settle.text
    data = settle.json()
    assert data["voucher_credit_cents"] == 2000
    assert data["paid_cents"] == 500
    assert data["remaining_cents"] == 0

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        payload = json.loads(order.payload_json)
        assert order.payment_status == "paid"
        assert payload["voucher_credit_cents"] == 2000
        assert payload["voucher_redemptions"][0]["voucher_definition_uuid"] == "vd-20"
    finally:
        db.close()


# --- Voucher sale lines ---


def test_voucher_sale_line_allowed_open_and_slips_print_at_settle(client):
    c, Session = client
    _swap_bundle(Session, bundle_copy(voucher_bundle()))

    r = _register_order(
        c,
        lines=[
            {"article_id": 20, "qty": 1, "note": "", "additions": []},
            {"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 1, "unit_cents": 2000, "note": "", "additions": []},
        ],
    )
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.job_kind == "voucher").count() == 0
    finally:
        db.close()

    summary = c.get(f"/v1/orders/{oid}/summary")
    assert summary.status_code == 200
    assert summary.json()["total_cents"] == 2500

    settle = _settle(c, oid, selections=[_sel(20, 1)], payments=[{"type": "cash", "amount_cents": 2500}])
    assert settle.status_code == 200, settle.text
    assert settle.json()["remaining_cents"] == 0

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.job_kind == "voucher").count() == 1
        order = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        assert order.payment_status == "paid"
    finally:
        db.close()


def test_voucher_sale_order_rejects_partial_settle(client):
    c, Session = client
    _swap_bundle(Session, bundle_copy(voucher_bundle()))

    r = _register_order(
        c,
        lines=[
            {"article_id": 20, "qty": 2, "note": "", "additions": []},
            {"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 1, "unit_cents": 2000, "note": "", "additions": []},
        ],
    )
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    settle = _settle(c, oid, selections=[_sel(20, 1)], payments=[{"type": "cash", "amount_cents": 500}])
    assert settle.status_code == 400


# --- Collective bill assignment ---


def test_assign_order_to_new_collective_bill(client):
    c, Session = client
    r = _register_order(c, lines=[{"article_id": 20, "qty": 2, "note": "", "additions": []}])
    oid = r.json()["local_order_id"]

    assign = c.post(
        f"/v1/orders/{oid}/assign-collective",
        json={"event_id": 1, "selections": [_sel(20, 2)], "new_name": "Verein"},
    )
    assert assign.status_code == 200, assign.text
    data = assign.json()
    assert data["name"] == "Verein"
    assert data["local_order_id"] == oid

    db = Session()
    try:
        bill = db.query(CollectiveBill).filter(CollectiveBill.id == data["collective_bill_id"]).one()
        original = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        assert original.payment_status == "paid"  # fully drained
        bill_orders = db.query(LocalOrder).filter(LocalOrder.collective_bill_id == bill.id).all()
        assert len(bill_orders) == 1
        bill_payload = json.loads(bill_orders[0].payload_json)
        assert bill_payload["lines"][0]["qty"] == 2
    finally:
        db.close()

    bills = c.get("/v1/collective-bills/open", params={"event_id": 1})
    rows = bills.json()["collective_bills"]
    assert len(rows) == 1
    assert rows[0]["total_cents"] == 1000


def test_assign_partial_selection_to_existing_bill(client):
    c, _ = client
    created = c.post("/v1/collective-bills", json={"event_id": 1, "name": "Stamm"})
    bill_id = created.json()["id"]

    r = _register_order(c, lines=[{"article_id": 20, "qty": 2, "note": "", "additions": []}])
    oid = r.json()["local_order_id"]

    assign = c.post(
        f"/v1/orders/{oid}/assign-collective",
        json={"event_id": 1, "selections": [_sel(20, 1)], "collective_bill_id": bill_id},
    )
    assert assign.status_code == 200, assign.text

    summary = c.get(f"/v1/orders/{oid}/summary")
    assert summary.status_code == 200
    assert summary.json()["total_cents"] == 500


def test_assign_collective_rejected_for_voucher_sale_order(client):
    c, Session = client
    _swap_bundle(Session, bundle_copy(voucher_bundle()))

    r = _register_order(
        c,
        lines=[
            {"article_id": 20, "qty": 1, "note": "", "additions": []},
            {"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 1, "unit_cents": 2000, "note": "", "additions": []},
        ],
    )
    oid = r.json()["local_order_id"]
    assign = c.post(
        f"/v1/orders/{oid}/assign-collective",
        json={"event_id": 1, "selections": [_sel(20, 1)], "new_name": "Verein"},
    )
    assert assign.status_code == 400


# --- Register open-orders list ---


def test_register_open_orders_list(client):
    c, _ = client
    r1 = _register_order(c, lines=[{"article_id": 20, "qty": 2, "note": "", "additions": []}])
    oid1 = r1.json()["local_order_id"]
    r2 = _register_order(c)
    oid2 = r2.json()["local_order_id"]
    # A paid-at-create order must not appear.
    r3 = _register_order(c, payments=[{"type": "cash", "amount_cents": 500}])
    assert r3.status_code == 200, r3.text

    listing = c.get("/v1/registers/reg-1/open-orders", params={"event_id": 1})
    assert listing.status_code == 200, listing.text
    data = listing.json()
    assert data["currency"] == "CHF"
    rows = {o["local_order_id"]: o for o in data["orders"]}
    assert set(rows) == {oid1, oid2}
    assert rows[oid1]["total_cents"] == 1000
    assert rows[oid1]["item_count"] == 2
    assert rows[oid1]["pickup_code"] == "A1"

    settle = _settle(c, oid1, selections=[_sel(20, 2)], payments=[{"type": "cash", "amount_cents": 1000}])
    assert settle.status_code == 200, settle.text

    listing = c.get("/v1/registers/reg-1/open-orders", params={"event_id": 1})
    assert [o["local_order_id"] for o in listing.json()["orders"]] == [oid2]


def test_register_open_orders_unknown_register(client):
    c, _ = client
    assert c.get("/v1/registers/reg-unknown/open-orders", params={"event_id": 1}).status_code == 404
