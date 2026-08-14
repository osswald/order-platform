"""Station-scoped pickup codes for multi-station cash-register orders."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models import LocalOrder, PrintJob, StationPickup
from tests.fixtures_bundles import bundle_copy, cash_register_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    return bundle_copy(cash_register_bundle())


@pytest.fixture
def client(client_session):
    return client_session


def _multi_station_order(c, *, payments=None):
    body = {
        "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
        "event_id": 1,
        "table_number": None,
        "order_source": "cash_register",
        "cash_register_uuid": "reg-1",
        "lines": [
            {"article_id": 10, "qty": 1, "note": "", "additions": []},
            {"article_id": 20, "qty": 1, "note": "", "additions": []},
        ],
    }
    if payments is not None:
        body["payments"] = payments
    else:
        body["payments"] = [{"type": "cash", "amount_cents": 1700}]
    return c.post("/v1/orders", json=body)


def _single_station_order(c, article_id=20, amount_cents=500):
    return c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": None,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [{"article_id": article_id, "qty": 1, "note": "", "additions": []}],
            "payments": [{"type": "cash", "amount_cents": amount_cents}],
        },
    )


def test_multi_station_allocates_distinct_codes(client):
    c, Session = client
    r = _multi_station_order(c)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pickup_codes"] == ["A1", "A2"]
    assert body["pickup_code"] == "A1"
    assert len(body["customer_print_job_ids"]) == 2

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.id == body["local_order_id"]).one()
        pickups = (
            db.query(StationPickup)
            .filter(StationPickup.local_order_id == order.id)
            .order_by(StationPickup.id.asc())
            .all()
        )
        assert [(p.station_uuid, p.pickup_code) for p in pickups] == [
            ("st-kitchen", "A1"),
            ("st-bar", "A2"),
        ]
        payload = json.loads(order.payload_json)
        assert payload["pickup_code"] == "A1"
        assert [p["pickup_code"] for p in payload["pickups"]] == ["A1", "A2"]

        jobs = (
            db.query(PrintJob)
            .filter(PrintJob.local_order_id == order.id, PrintJob.job_kind == "customer_pickup")
            .all()
        )
        from app.print_render import ensure_print_job_payload

        texts = {
            j.station_uuid: ensure_print_job_payload(db, j).decode("cp858", errors="replace")
            for j in jobs
        }
        assert "A1" in texts["st-kitchen"]
        assert "A2" not in texts["st-kitchen"].split("A1")[0]  # hero is A1
        assert "A2" in texts["st-bar"]
    finally:
        db.close()


def test_single_station_unchanged(client):
    c, Session = client
    r = _single_station_order(c)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pickup_code"] == "A1"
    assert body["pickup_codes"] == ["A1"]
    assert body["pickup_status"] == "ready"
    assert len(body["customer_print_job_ids"]) == 1

    db = Session()
    try:
        pickups = db.query(StationPickup).all()
        assert len(pickups) == 1
        assert pickups[0].pickup_code == "A1"
        assert pickups[0].pickup_status == "ready"
    finally:
        db.close()


def test_purge_then_single_station_order_gets_one_code(client):
    from app.event_lifecycle import purge_event_local_data

    c, Session = client
    first = _single_station_order(c)
    assert first.status_code == 200, first.text
    assert first.json()["pickup_codes"] == ["A1"]

    db = Session()
    try:
        purge_event_local_data(db, 1)
        db.commit()
        assert db.query(StationPickup).count() == 0
        assert db.query(LocalOrder).count() == 0
    finally:
        db.close()

    second = _single_station_order(c)
    assert second.status_code == 200, second.text
    assert second.json()["pickup_code"] == "A1"
    assert second.json()["pickup_codes"] == ["A1"]

    db = Session()
    try:
        pickups = db.query(StationPickup).all()
        assert len(pickups) == 1
        assert pickups[0].pickup_code == "A1"
        assert pickups[0].local_order_id == second.json()["local_order_id"]
    finally:
        db.close()


def test_orphaned_pickups_on_reused_order_id_are_replaced(client):
    c, Session = client
    db = Session()
    try:
        db.add(
            StationPickup(
                local_order_id=1,
                event_id=1,
                station_uuid="st-kitchen",
                pickup_code="Z9",
                pickup_status="pending",
            )
        )
        db.commit()
        assert db.query(LocalOrder).count() == 0
    finally:
        db.close()

    r = _single_station_order(c)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["local_order_id"] == 1
    assert body["pickup_code"] == "A1"
    assert body["pickup_codes"] == ["A1"]

    db = Session()
    try:
        pickups = (
            db.query(StationPickup)
            .filter(StationPickup.local_order_id == 1)
            .order_by(StationPickup.id.asc())
            .all()
        )
        assert [(p.pickup_code, p.station_uuid) for p in pickups] == [("A1", "st-bar")]
        assert db.query(StationPickup).filter(StationPickup.pickup_code == "Z9").count() == 0
    finally:
        db.close()


def test_independent_ready_and_picked_up(client):
    c, Session = client
    r = _multi_station_order(c)
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.status_code == 200, pickup.text
    rows = {o["pickup_code"]: o for o in pickup.json()["orders"]}
    assert set(rows) == {"A1", "A2"}
    assert rows["A1"]["pickup_status"] == "pending"  # Grill kitchen
    assert rows["A2"]["pickup_status"] == "ready"  # Bar direct print
    assert rows["A1"]["local_order_id"] == oid
    assert "pickup_id" in rows["A1"]

    kitchen = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    assert kitchen.status_code == 200
    ticket = kitchen.json()["orders"][0]
    assert ticket["pickup_code"] == "A1"

    done = c.post(f"/v1/kitchen/tickets/{ticket['id']}/print")
    assert done.status_code == 200, done.text

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    rows = {o["pickup_code"]: o for o in pickup.json()["orders"]}
    assert rows["A1"]["pickup_status"] == "ready"
    assert rows["A2"]["pickup_status"] == "ready"

    picked = c.post(f"/v1/pickup/pickups/{rows['A1']['pickup_id']}/picked-up")
    assert picked.status_code == 200, picked.text
    assert picked.json()["pickup_status"] == "picked_up"

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    remaining = [o["pickup_code"] for o in pickup.json()["orders"]]
    assert remaining == ["A2"]


def test_open_orders_one_row_with_all_codes(client):
    c, _ = client
    r = _multi_station_order(c, payments=[])
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    listing = c.get("/v1/registers/reg-1/open-orders", params={"event_id": 1})
    assert listing.status_code == 200, listing.text
    orders = listing.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["local_order_id"] == oid
    assert orders[0]["pickup_code"] == "A1"
    assert orders[0]["pickup_codes"] == ["A1", "A2"]


def test_open_order_summary_includes_station_pickups(client):
    c, _ = client
    r = _multi_station_order(c, payments=[])
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    summary = c.get(f"/v1/orders/{oid}/summary")
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data["pickup_codes"] == ["A1", "A2"]
    assert [(p["station_uuid"], p["pickup_code"]) for p in data["pickups"]] == [
        ("st-kitchen", "A1"),
        ("st-bar", "A2"),
    ]


def test_partial_settle_keeps_station_pickups_on_original(client):
    c, Session = client
    r = _multi_station_order(c, payments=[])
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    settle = c.post(
        f"/v1/orders/{oid}/settle-partial",
        json={
            "event_id": 1,
            "selections": [{"article_id": 20, "qty": 1, "note": "", "additions": []}],
            "payments": [{"type": "cash", "amount_cents": 500}],
        },
    )
    assert settle.status_code == 200, settle.text

    db = Session()
    try:
        original = db.query(LocalOrder).filter(LocalOrder.id == oid).one()
        assert original.payment_status == "open"
        pickups = (
            db.query(StationPickup)
            .filter(StationPickup.local_order_id == oid)
            .order_by(StationPickup.id.asc())
            .all()
        )
        assert [p.pickup_code for p in pickups] == ["A1", "A2"]
        paid = (
            db.query(LocalOrder)
            .filter(LocalOrder.payment_status == "paid", LocalOrder.id != oid)
            .all()
        )
        assert paid
        for porder in paid:
            assert db.query(StationPickup).filter(StationPickup.local_order_id == porder.id).count() == 0
    finally:
        db.close()


def test_ready_ttl_expires_station_pickup_independently(client):
    c, Session = client
    r = _multi_station_order(c)
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    db = Session()
    try:
        bar = (
            db.query(StationPickup)
            .filter(StationPickup.local_order_id == oid, StationPickup.pickup_code == "A2")
            .one()
        )
        bar.ready_at = datetime.now(UTC) - timedelta(minutes=10)
        db.commit()
        bar_id = bar.id
    finally:
        db.close()

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    codes = {o["pickup_code"] for o in pickup.json()["orders"]}
    assert "A2" not in codes
    assert "A1" in codes

    db = Session()
    try:
        assert db.query(StationPickup).filter(StationPickup.id == bar_id).one().pickup_status == "picked_up"
    finally:
        db.close()


def _slip_text(db, job: PrintJob) -> str:
    from app.print_render import ensure_print_job_payload

    return ensure_print_job_payload(db, job).decode("cp858", errors="replace")


def _render_pickup_code(job: PrintJob) -> str | None:
    ctx = json.loads(job.render_context_json or "{}")
    payload = ctx.get("payload") if isinstance(ctx, dict) else None
    if not isinstance(payload, dict):
        return None
    code = payload.get("pickup_code")
    return str(code) if code else None


def test_direct_station_print_includes_station_pickup_code(client):
    """Bar has no kitchen monitor → station_order slip must hero that station's code."""
    c, Session = client
    r = _multi_station_order(c)
    assert r.status_code == 200, r.text
    oid = r.json()["local_order_id"]

    db = Session()
    try:
        job = (
            db.query(PrintJob)
            .filter(
                PrintJob.local_order_id == oid,
                PrintJob.job_kind == "station_order",
                PrintJob.station_uuid == "st-bar",
            )
            .one()
        )
        assert _render_pickup_code(job) == "A2"
        text = _slip_text(db, job)
        assert "A2" in text
    finally:
        db.close()


def test_kitchen_print_uses_station_code_not_first_order_code(client):
    """Kitchen station allocated second: list shows A2; printed slip must also use A2, not A1."""
    c, Session = client
    # Bar line first → A1 (direct); Grill line second → A2 (kitchen monitor)
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": None,
            "order_source": "cash_register",
            "cash_register_uuid": "reg-1",
            "lines": [
                {"article_id": 20, "qty": 1, "note": "", "additions": []},
                {"article_id": 10, "qty": 1, "note": "", "additions": []},
            ],
            "payments": [{"type": "cash", "amount_cents": 1700}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pickup_codes"] == ["A1", "A2"]
    assert body["pickup_code"] == "A1"
    oid = body["local_order_id"]

    kitchen = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    assert kitchen.status_code == 200, kitchen.text
    ticket = kitchen.json()["orders"][0]
    assert ticket["pickup_code"] == "A2"
    assert ticket["local_order_id"] == oid

    printed = c.post(f"/v1/kitchen/tickets/{ticket['id']}/print")
    assert printed.status_code == 200, printed.text
    job_id = printed.json()["print_job_id"]
    assert job_id

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.job_kind == "kitchen_ticket"
        assert _render_pickup_code(job) == "A2"
        text = _slip_text(db, job)
        assert "A2" in text
    finally:
        db.close()
