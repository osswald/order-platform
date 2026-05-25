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
    voucher_jobs = [
        j
        for j in jobs
        if b"GUTSCHEIN" in base64.b64decode(j.escpos_payload or "")
    ]
    assert len(voucher_jobs) == 2


def test_settle_partial_with_amount_voucher_credit(client):
    c, Session = client
    db = Session()
    db.add(
        LocalOrder(
            client_order_id="v-open-1",
            event_id=1,
            table_number=4,
            payment_status="open",
            payload_json=json.dumps(
                {
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
                }
            ),
        )
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
    c, Session = client
    db = Session()
    db.add(
        LocalOrder(
            client_order_id="v-art-1",
            event_id=1,
            table_number=7,
            payment_status="open",
            payload_json=json.dumps(
                {
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
                }
            ),
        )
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
