"""Load-test job: actors, gates, API, single-flight."""

from __future__ import annotations

import json
import random
import time

import pytest
from app.load_test_job import (
    get_status,
    place_one_order,
    reset_load_test_state_for_tests,
    start_load_test,
    stop_load_test,
    wait_until_idle_for_tests,
)
from app.models import LocalOrder, PaymentReceipt, PrintJob, SyncedBundle
from fastapi import HTTPException
from tests.fixtures_bundles import bundle_copy, cash_register_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


def _load_test_bundle():
    b = bundle_copy(cash_register_bundle())
    ev = b["events"][0]
    ev["status"] = "test"
    ev["configuration"]["event_waiters"] = [
        {"uuid": "w-1", "name": "Anna"},
        {"uuid": "w-2", "name": "Ben"},
    ]
    ev["configuration"]["cash_registers"][0]["cash_drawer_command"] = "escp_pin2"
    ev["configuration"]["cash_registers"].append(
        {
            "uuid": "reg-2",
            "name": "Nebenkasse",
            "sort_order": 1,
            "pickup_code_prefix": "B",
            "layout_uuid": "layout-1",
            "cash_drawer_command": "escp_pin2",
        }
    )
    ev["printer_hosts"]["reg-2"] = "127.0.0.1:9100"
    ev["articles"]["99"] = {"id": 99, "name": "Sauce", "price": 1.0, "sellable": True, "additions": []}
    ev["articles"]["10"]["additions"] = [
        {"article_id": 99, "name": "Sauce", "price": 1.0, "preselected": True},
    ]
    return b


@pytest.fixture
def bundle():
    return _load_test_bundle()


@pytest.fixture
def client(client_session):
    return client_session


@pytest.fixture(autouse=True)
def _reset_load_test():
    reset_load_test_state_for_tests()
    yield
    reset_load_test_state_for_tests()


def _swap_bundle(Session, new_bundle):
    from app.bundle_cache import invalidate_bundle_cache

    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).one()
        row.json_body = json.dumps(new_bundle)
        db.commit()
        invalidate_bundle_cache()
    finally:
        db.close()


def test_place_waiter_order_settled(client):
    _c, Session = client
    db = Session()
    try:
        from app.bundle_cache import get_bundle_dict

        event = get_bundle_dict(db)["events"][0]
        result = place_one_order(
            db,
            event=event,
            event_id=1,
            actor_kind="waiter",
            actor_uuid="w-1",
            table_number=7,
            rng=random.Random(1),
            receipt_probability=0.0,
        )
        order = db.query(LocalOrder).filter(LocalOrder.id == result["local_order_id"]).one()
        assert order.payment_status == "paid"
        assert order.table_number == 7
        assert db.query(PaymentReceipt).count() >= 1
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() == 0
    finally:
        db.close()


def test_place_register_order_kicks_drawer(client):
    _c, Session = client
    db = Session()
    try:
        from app.bundle_cache import get_bundle_dict

        event = get_bundle_dict(db)["events"][0]
        result = place_one_order(
            db,
            event=event,
            event_id=1,
            actor_kind="register",
            actor_uuid="reg-1",
            table_number=None,
            rng=random.Random(2),
            receipt_probability=0.0,
        )
        order = db.query(LocalOrder).filter(LocalOrder.id == result["local_order_id"]).one()
        assert order.payment_status == "paid"
        assert order.cash_register_uuid == "reg-1"
        assert db.query(PrintJob).filter(PrintJob.job_kind == "cash_drawer").count() >= 1
    finally:
        db.close()


def test_receipt_print_probability_deterministic(client):
    _c, Session = client
    db = Session()
    try:
        from app.bundle_cache import get_bundle_dict

        event = get_bundle_dict(db)["events"][0]
        printed = 0
        trials = 40
        for seed in range(trials):
            result = place_one_order(
                db,
                event=event,
                event_id=1,
                actor_kind="register",
                actor_uuid="reg-1",
                table_number=None,
                rng=random.Random(seed),
                receipt_probability=0.30,
            )
            if result["receipt_printed"]:
                printed += 1
        assert 4 <= printed <= 22
        assert db.query(PrintJob).filter(PrintJob.job_kind == "payment_receipt").count() == printed
    finally:
        db.close()


def test_receipt_skipped_when_no_print_target(client):
    _c, Session = client
    b = _load_test_bundle()
    b["events"][0]["printer_hosts"] = {}
    _swap_bundle(Session, b)
    db = Session()
    try:
        from app.bundle_cache import get_bundle_dict

        event = get_bundle_dict(db)["events"][0]
        result = place_one_order(
            db,
            event=event,
            event_id=1,
            actor_kind="waiter",
            actor_uuid="w-1",
            table_number=1,
            rng=random.Random(0),
            receipt_probability=1.0,
        )
        assert result["receipt_printed"] is False
        assert db.query(PrintJob).filter(PrintJob.job_kind == "payment_receipt").count() == 0
    finally:
        db.close()


def test_start_rejects_non_test(client):
    _c, Session = client
    b = _load_test_bundle()
    b["events"][0]["status"] = "prod"
    _swap_bundle(Session, b)
    with pytest.raises(HTTPException) as ei:
        start_load_test(
            event_id=1,
            waiter_count=1,
            cash_register_count=0,
            table_min=1,
            table_max=5,
            total_orders=1,
            burst_interval_seconds=0.05,
        )
    assert ei.value.status_code == 409
    assert get_status()["state"] == "idle"


def test_job_aborts_when_status_leaves_test(client):
    _c, Session = client
    status = start_load_test(
        event_id=1,
        waiter_count=1,
        cash_register_count=0,
        table_min=1,
        table_max=5,
        total_orders=20,
        burst_interval_seconds=0.15,
        rng_seed=1,
    )
    assert status["state"] == "running"
    time.sleep(0.25)
    b = _load_test_bundle()
    b["events"][0]["status"] = "prod"
    _swap_bundle(Session, b)
    st = wait_until_idle_for_tests(timeout=5.0)
    assert st["state"] == "failed"
    assert "test" in (st.get("last_error") or "").lower()


def test_single_flight_and_stop(client):
    _c, Session = client
    start_load_test(
        event_id=1,
        waiter_count=1,
        cash_register_count=1,
        table_min=1,
        table_max=10,
        total_orders=50,
        burst_interval_seconds=0.2,
        rng_seed=3,
    )
    with pytest.raises(HTTPException) as ei:
        start_load_test(
            event_id=1,
            waiter_count=1,
            cash_register_count=0,
            table_min=1,
            table_max=5,
            total_orders=1,
            burst_interval_seconds=0.05,
        )
    assert ei.value.status_code == 409
    stop_load_test()
    st = wait_until_idle_for_tests(timeout=5.0)
    assert st["state"] == "done"


def test_api_start_status_stop(client):
    c, Session = client
    idle = c.get("/v1/load-test/status")
    assert idle.status_code == 200
    assert idle.json()["state"] == "idle"

    started = c.post(
        "/v1/load-test/start",
        json={
            "event_id": 1,
            "waiter_count": 1,
            "cash_register_count": 0,
            "table_min": 1,
            "table_max": 5,
            "total_orders": 2,
            "burst_interval_seconds": 0.05,
            "rng_seed": 9,
        },
    )
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["state"] == "running"
    assert body["config"]["waiter_count"] == 1
    assert body["config"]["actors_per_burst"] == 1

    c.post("/v1/load-test/stop")
    wait_until_idle_for_tests(timeout=5.0)

    capped = c.post(
        "/v1/load-test/start",
        json={
            "event_id": 1,
            "waiter_count": 99,
            "cash_register_count": 99,
            "table_min": 1,
            "table_max": 5,
            "total_orders": 3,
            "burst_interval_seconds": 0.05,
            "rng_seed": 4,
        },
    )
    assert capped.status_code == 200, capped.text
    cfg = capped.json()["config"]
    assert cfg["waiter_count"] == 2
    assert cfg["cash_register_count"] == 2
    assert cfg["actors_per_burst"] == 4

    st = wait_until_idle_for_tests(timeout=8.0)
    assert st["state"] == "done"
    assert st["placed"] + st["failed"] == 3


def test_api_rejects_non_test(client):
    c, Session = client
    b = _load_test_bundle()
    b["events"][0]["status"] = "config"
    _swap_bundle(Session, b)
    r = c.post(
        "/v1/load-test/start",
        json={
            "event_id": 1,
            "waiter_count": 1,
            "cash_register_count": 0,
            "table_min": 1,
            "table_max": 5,
            "total_orders": 1,
            "burst_interval_seconds": 0.05,
        },
    )
    assert r.status_code == 409


def test_reset_leaves_idle():
    reset_load_test_state_for_tests()
    assert get_status()["state"] == "idle"
    assert get_status()["placed"] == 0
