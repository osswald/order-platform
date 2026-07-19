"""Voucher sale prints and settle-partial redemption."""

import base64
import json
import uuid

import pytest
from app.models import LocalOrder, PrintJob
from tests.fixtures_bundles import bundle_copy, voucher_bundle


@pytest.fixture
def bundle():
    return bundle_copy(voucher_bundle())


@pytest.fixture
def client(client_session):
    return client_session


def test_register_voucher_sale_creates_print_jobs_per_unit(client):
    c, Session = client
    cid = f"reg-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 2,
                    "unit_cents": 2000,
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 4000}],
        },
    )
    assert r.status_code == 200, r.text
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    jobs = db.query(PrintJob).filter(PrintJob.local_order_id == order.id).all()
    db.close()
    voucher_jobs = [j for j in jobs if b"GUTSCHEIN" in base64.b64decode(j.escpos_payload or "")]
    assert len(voucher_jobs) == 2


def test_register_voucher_only_single_print_job_no_pickup_slip(client):
    """Voucher-only cash register order: one receipt slip per unit, no station/pickup 0.00 slips."""
    c, Session = client
    cid = f"reg-vo-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                    "unit_cents": 2000,
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 2000}],
        },
    )
    assert r.status_code == 200, r.text
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    jobs = db.query(PrintJob).filter(PrintJob.local_order_id == order.id).all()
    db.close()
    assert len(jobs) == 1
    slip = base64.b64decode(jobs[0].escpos_payload or "")
    text = slip.decode("cp858", errors="replace")
    assert b"GUTSCHEIN" in slip
    assert "20 CHF Gutschein" in text or "Gutschein" in text
    assert "20.00" not in text
    assert " 0.00" not in text
    assert "Abholcode" not in text


def test_settle_partial_with_amount_voucher_credit(client):
    from tests.seed_orders import seed_open_submission

    c, Session = client
    db = Session()
    seed_open_submission(
        db,
        client_order_id="v-open-1",
        event_id=1,
        table_number=4,
        payload={
            "event_id": 1,
            "table_number": 4,
            "payment_status": "open",
            "lines": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [],
                    "unit_cents": 500,
                }
            ],
        },
    )
    db.commit()
    db.close()

    r = c.post(
        "/v1/tables/4/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 0}],
            "selections": [{"article_id": 20, "qty": 1, "note": "", "additions": []}],
            "voucher_redemptions": [{"voucher_definition_uuid": "vd-20"}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["paid_cents"] == 0
    assert body["voucher_credit_cents"] == 500


def test_register_order_with_amount_voucher_redemption(client):
    c, Session = client
    cid = f"reg-vr-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {"article_id": 20, "qty": 1, "note": "", "additions": []},
            ],
            "voucher_redemptions": [{"voucher_definition_uuid": "vd-20"}],
            "payments": [{"type": "cash", "amount_cents": 0}],
        },
    )
    assert r.status_code == 200, r.text
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    payload = json.loads(order.payload_json or "{}")
    db.close()
    assert payload.get("voucher_credit_cents") == 500


def test_settle_partial_with_article_entitlement_voucher(client):
    from tests.seed_orders import seed_open_submission

    c, Session = client
    db = Session()
    seed_open_submission(
        db,
        client_order_id="v-art-1",
        event_id=1,
        table_number=7,
        payload={
            "event_id": 1,
            "table_number": 7,
            "payment_status": "open",
            "lines": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
        },
    )
    db.commit()
    db.close()

    r = c.post(
        "/v1/tables/7/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 0}],
            "selections": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
            "voucher_redemptions": [
                {
                    "voucher_definition_uuid": "vd-drink",
                    "article_id": 20,
                    "note": "",
                    "qty": 1,
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["voucher_credit_cents"] == 500
    assert body["paid_cents"] == 0


def test_article_entitlement_credits_one_unit_when_qty_two(client):
    from tests.seed_orders import seed_open_submission

    c, Session = client
    db = Session()
    seed_open_submission(
        db,
        client_order_id="v-qty2-1",
        event_id=1,
        table_number=8,
        payload={
            "event_id": 1,
            "table_number": 8,
            "payment_status": "open",
            "lines": [
                {
                    "article_id": 20,
                    "qty": 2,
                    "note": "",
                    "additions": [],
                    "unit_cents": 500,
                }
            ],
        },
    )
    db.commit()
    db.close()

    r = c.post(
        "/v1/tables/8/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 500}],
            "selections": [{"article_id": 20, "qty": 2, "note": "", "additions": []}],
            "voucher_redemptions": [
                {
                    "voucher_definition_uuid": "vd-wurst",
                    "article_id": 20,
                    "note": "",
                    "qty": 2,
                    "additions": [],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["voucher_credit_cents"] == 500


def _bundle_with_salat_addon(bundle: dict) -> dict:
    from tests.fixtures_bundles import bundle_copy

    b = bundle_copy(bundle)
    event = b["events"][0]
    event["articles"]["99"] = {"id": 99, "name": "Salat", "price": 3.0, "additions": []}
    event["articles"]["20"]["additions"] = [{"article_id": 99, "name": "Salat", "price": 3.0}]
    return b


def test_article_entitlement_base_only_with_addon_line(client, bundle):
    import json

    from app.models import SyncedBundle
    from tests.seed_orders import seed_open_submission

    b = _bundle_with_salat_addon(bundle)
    c, Session = client
    db = Session()
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    row.json_body = json.dumps(b)
    seed_open_submission(
        db,
        client_order_id="v-addon-1",
        event_id=1,
        table_number=9,
        payload={
            "event_id": 1,
            "table_number": 9,
            "payment_status": "open",
            "lines": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
        },
    )
    db.commit()
    db.close()

    r = c.post(
        "/v1/tables/9/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 300}],
            "selections": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
            "voucher_redemptions": [
                {
                    "voucher_definition_uuid": "vd-wurst",
                    "article_id": 20,
                    "note": "",
                    "qty": 1,
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["voucher_credit_cents"] == 500
    assert body["paid_cents"] == 300


def test_article_entitlement_include_additions_credits_full_line_unit(client, bundle):
    import json

    from app.models import SyncedBundle
    from tests.seed_orders import seed_open_submission

    b = _bundle_with_salat_addon(bundle)
    c, Session = client
    db = Session()
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    row.json_body = json.dumps(b)
    db.commit()
    seed_open_submission(
        db,
        client_order_id="v-full-1",
        event_id=1,
        table_number=10,
        payload={
            "event_id": 1,
            "table_number": 10,
            "payment_status": "open",
            "lines": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
        },
    )
    db.commit()
    db.close()

    r = c.post(
        "/v1/tables/10/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 0}],
            "selections": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
            "voucher_redemptions": [
                {
                    "voucher_definition_uuid": "vd-drink",
                    "article_id": 20,
                    "note": "",
                    "qty": 1,
                    "additions": [{"article_id": 99, "qty": 1}],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["voucher_credit_cents"] == 800


def test_voucher_sale_ignores_spoofed_unit_cents(client):
    """Server prices from definition; client unit_cents must not change the total."""
    c, Session = client
    cid = f"reg-spoof-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                    "unit_cents": 1,
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 1}],
        },
    )
    assert r.status_code == 400, r.text

    cid2 = f"reg-ok-{uuid.uuid4().hex[:10]}"
    r2 = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid2,
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                    "unit_cents": 1,
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 2000}],
        },
    )
    assert r2.status_code == 200, r2.text
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid2).first()
    payload = json.loads(order.payload_json or "{}")
    db.close()
    assert payload["payment_status"] == "paid"
    assert payload["payments"][0]["amount_cents"] == 2000


def test_voucher_sale_rejects_unknown_definition(client):
    c, _Session = client
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"reg-unk-{uuid.uuid4().hex[:10]}",
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-missing",
                    "qty": 1,
                    "unit_cents": 500,
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 500}],
        },
    )
    assert r.status_code == 400, r.text
    assert "voucher" in r.text.lower() or "Unknown" in r.text


def test_voucher_sale_rejects_article_entitlement_definition(client):
    c, _Session = client
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"reg-ent-{uuid.uuid4().hex[:10]}",
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-drink",
                    "qty": 1,
                    "unit_cents": 500,
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 500}],
        },
    )
    assert r.status_code == 400, r.text
    assert "fixed_amount" in r.text or "sold" in r.text.lower()


def test_open_register_voucher_sale_prints_at_create(client):
    c, Session = client
    cid = f"reg-open-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                }
            ],
            "payments": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "open"
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    jobs = [j for j in db.query(PrintJob).filter(PrintJob.local_order_id == order.id).all() if j.job_kind == "voucher"]
    db.close()
    assert len(jobs) == 1


def test_waiter_unpaid_voucher_sale_allowed(client):
    c, Session = client
    cid = f"w-open-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": 3,
            "order_source": "waiter",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                }
            ],
            "payments": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "open"
    assert body["voucher_escpos_payloads"] == []
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    assert order.payment_status == "open"
    voucher_jobs = (
        db.query(PrintJob).filter(PrintJob.local_order_id == order.id, PrintJob.job_kind == "voucher").count()
    )
    db.close()
    assert voucher_jobs == 0


def test_waiter_voucher_bluetooth_returns_escpos_payloads(client):
    c, Session = client
    cid = f"w-bt-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": 3,
            "order_source": "waiter",
            "voucher_print_via_bluetooth": True,
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 2,
                }
            ],
            "payments": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "open"
    assert len(body["voucher_escpos_payloads"]) == 2
    assert len(body["voucher_names"]) == 2
    for payload in body["voucher_escpos_payloads"]:
        assert b"GUTSCHEIN" in base64.b64decode(payload)
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    voucher_jobs = (
        db.query(PrintJob).filter(PrintJob.local_order_id == order.id, PrintJob.job_kind == "voucher").count()
    )
    db.close()
    assert voucher_jobs == 0


def test_waiter_voucher_network_target_creates_print_jobs(client):
    c, Session = client
    cid = f"w-net-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": 3,
            "order_source": "waiter",
            "voucher_printer_station_uuid": "reg-1",
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                }
            ],
            "payments": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "open"
    assert body["voucher_escpos_payloads"] == []
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    jobs = db.query(PrintJob).filter(PrintJob.local_order_id == order.id, PrintJob.job_kind == "voucher").all()
    db.close()
    assert len(jobs) == 1
    assert jobs[0].station_uuid == "reg-1"


def test_waiter_instant_voucher_sale_attaches_to_collective(client, bundle):
    from app.models import SyncedBundle
    from tests.fixtures_bundles import bundle_copy

    b = bundle_copy(bundle)
    b["events"][0]["payment_mode"] = "instant"
    b["events"][0]["instant_collective_bill_uuid"] = "instant-bill-1"
    b["events"][0]["instant_collective_bill_name"] = "Sofort"
    c, Session = client
    db = Session()
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    row.json_body = json.dumps(b)
    db.commit()
    db.close()

    cid = f"w-inst-{uuid.uuid4().hex[:10]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": 3,
            "order_source": "waiter",
            "voucher_print_via_bluetooth": True,
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                }
            ],
            "payments": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_status"] == "paid"
    assert len(body["voucher_escpos_payloads"]) == 1
    db = Session()
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    assert order.payment_status == "paid"
    assert order.collective_bill_id is not None
    db.close()


def test_redemption_credit_does_not_reduce_voucher_sale_face_value(client):
    """Fixed-amount redemption credits article gross only; voucher face stays payable."""
    from tests.seed_orders import seed_open_submission

    c, Session = client
    db = Session()
    seed_open_submission(
        db,
        client_order_id="v-mix-1",
        event_id=1,
        table_number=11,
        payload={
            "event_id": 1,
            "table_number": 11,
            "payment_status": "open",
            "lines": [
                {
                    "article_id": 20,
                    "qty": 1,
                    "note": "",
                    "additions": [],
                    "unit_cents": 500,
                },
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                    "unit_cents": 2000,
                },
            ],
        },
    )
    db.commit()
    db.close()

    # Article 500 - credit 500 = 0, plus voucher face 2000 => payable 2000
    r = c.post(
        "/v1/tables/11/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 2000}],
            "selections": [
                {"kind": "article", "article_id": 20, "qty": 1, "note": "", "additions": []},
                {"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 1},
            ],
            "voucher_redemptions": [{"voucher_definition_uuid": "vd-20"}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["voucher_credit_cents"] == 500
    assert body["paid_cents"] == 2000
