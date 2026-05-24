"""Cash-register orders, pickup codes, and pickup screen state."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import KitchenTicket, LocalOrder, PrintJob, RegisterDisplayState, SyncedBundle


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.database as database

    monkeypatch.setenv("PRINT_TO_FILE", "1")
    monkeypatch.setenv("PRINT_OUTPUT_DIR", str(tmp_path))

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    Session = database.SessionLocal
    db = Session()
    bundle = {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "currency": "CHF",
                "payment_mode": "pay_later",
                "payment_types": ["cash"],
                "printer_hosts": {
                    "reg-1": "127.0.0.1:9100",
                    "st-kitchen": "127.0.0.1:9100",
                    "st-bar": "127.0.0.1:9100",
                },
                "articles": {
                    "10": {"id": 10, "name": "Burger", "price": 12.0, "additions": []},
                    "20": {"id": 20, "name": "Bier", "price": 5.0, "additions": []},
                },
                "configuration": {
                    "stations": [
                        {
                            "uuid": "st-kitchen",
                            "name": "Grill",
                            "sort_order": 0,
                            "kitchen_monitor_enabled": True,
                            "article_ids": [10],
                        },
                        {
                            "uuid": "st-bar",
                            "name": "Bar",
                            "sort_order": 1,
                            "kitchen_monitor_enabled": False,
                            "article_ids": [20],
                        },
                    ],
                    "event_waiters": [],
                    "app_layouts": [
                        {
                            "uuid": "layout-1",
                            "name": "Kasse",
                            "is_default": True,
                            "grid_width": 1,
                            "grid_height": 1,
                            "cells": [],
                        }
                    ],
                    "cash_registers": [
                        {
                            "uuid": "reg-1",
                            "name": "Hauptkasse",
                            "sort_order": 0,
                            "pickup_code_prefix": "A",
                            "layout_uuid": "layout-1",
                        }
                    ],
                },
            }
        ],
    }
    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()
    db.close()

    from app.routers import edge_api

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[edge_api.get_db] = override_get_db
    with TestClient(app) as c:
        yield c, Session
    app.dependency_overrides.clear()


def _cash_register_order(c, article_id=20, amount_cents=500):
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


def test_cash_register_order_gets_paid_pickup_code_and_customer_print(client):
    c, Session = client
    r1 = _cash_register_order(c)
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["pickup_code"] == "A1"
    assert body1["payment_status"] == "paid"
    assert body1["pickup_status"] == "ready"
    assert len(body1["customer_print_job_ids"]) == 1

    r2 = _cash_register_order(c)
    assert r2.status_code == 200, r2.text
    assert r2.json()["pickup_code"] == "A2"

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.pickup_code == "A1").one()
        payload = json.loads(order.payload_json)
        assert order.table_number == 0
        assert payload["table_number"] is None
        assert order.payment_status == "paid"
        assert db.query(PrintJob).filter(PrintJob.local_order_id == order.id).count() == 2
    finally:
        db.close()


def test_cash_register_kitchen_order_moves_from_pending_to_ready(client):
    c, Session = client
    r = _cash_register_order(c, article_id=10, amount_cents=1200)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pickup_code"] == "A1"
    assert body["pickup_status"] == "pending"

    kitchen = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    assert kitchen.status_code == 200
    ticket = kitchen.json()["orders"][0]
    assert ticket["pickup_code"] == "A1"

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.status_code == 200
    assert pickup.json()["orders"][0]["pickup_status"] == "pending"

    done = c.post(f"/v1/kitchen/tickets/{ticket['id']}/print")
    assert done.status_code == 200, done.text

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.status_code == 200
    assert pickup.json()["orders"][0]["pickup_status"] == "ready"

    picked = c.post(f"/v1/pickup/orders/{pickup.json()['orders'][0]['local_order_id']}/picked-up")
    assert picked.status_code == 200
    assert c.get("/v1/pickup/orders", params={"event_id": 1}).json()["orders"] == []

    db = Session()
    try:
        assert db.query(KitchenTicket).one().status == "done"
    finally:
        db.close()


def test_register_display_state_round_trip(client):
    c, Session = client
    body = {
        "event_id": 1,
        "payload": {"state": "ordering", "total_cents": 500, "lines": [{"article_id": 20, "qty": 1}]},
    }
    put = c.put("/v1/registers/reg-1/display", json=body)
    assert put.status_code == 200, put.text
    get = c.get("/v1/registers/reg-1/display", params={"event_id": 1})
    assert get.status_code == 200
    assert get.json()["payload"]["total_cents"] == 500

    db = Session()
    try:
        assert db.query(RegisterDisplayState).filter(RegisterDisplayState.cash_register_uuid == "reg-1").count() == 1
    finally:
        db.close()


def test_register_display_twint_payload(client):
    c, _ = client
    twint_body = {
        "event_id": 1,
        "payload": {
            "state": "twint",
            "show_twint": True,
            "twint_qr_data_url": "data:image/png;base64,abc",
            "total_cents": 1250,
            "lines": [{"article_id": 20, "qty": 1}],
        },
    }
    put = c.put("/v1/registers/reg-1/display", json=twint_body)
    assert put.status_code == 200, put.text
    get = c.get("/v1/registers/reg-1/display", params={"event_id": 1})
    payload = get.json()["payload"]
    assert payload["state"] == "twint"
    assert payload["twint_qr_data_url"].startswith("data:image/png")
    assert payload["total_cents"] == 1250


def test_ready_pickup_orders_expire_after_five_minutes(client):
    c, Session = client
    r = _cash_register_order(c, article_id=10, amount_cents=1200)
    assert r.status_code == 200, r.text

    kitchen = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    ticket = kitchen.json()["orders"][0]
    done = c.post(f"/v1/kitchen/tickets/{ticket['id']}/print")
    assert done.status_code == 200, done.text

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.status_code == 200
    assert pickup.json()["orders"][0]["pickup_status"] == "ready"

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.pickup_code == "A1").one()
        order.ready_at = datetime.now(timezone.utc) - timedelta(minutes=6)
        db.commit()
    finally:
        db.close()

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.status_code == 200
    assert pickup.json()["orders"] == []

    db = Session()
    try:
        order = db.query(LocalOrder).filter(LocalOrder.pickup_code == "A1").one()
        assert order.pickup_status == "picked_up"
        assert order.picked_up_at is not None
    finally:
        db.close()


def test_ready_pickup_orders_sorted_by_ready_at(client):
    c, _ = client
    kitchen_order = _cash_register_order(c, article_id=10, amount_cents=1200)
    assert kitchen_order.status_code == 200, kitchen_order.text

    instant_order = _cash_register_order(c, article_id=20, amount_cents=500)
    assert instant_order.status_code == 200, instant_order.text
    assert instant_order.json()["pickup_code"] == "A2"
    assert instant_order.json()["pickup_status"] == "ready"

    kitchen = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    ticket = kitchen.json()["orders"][0]
    done = c.post(f"/v1/kitchen/tickets/{ticket['id']}/print")
    assert done.status_code == 200, done.text

    pickup = c.get("/v1/pickup/orders", params={"event_id": 1})
    assert pickup.status_code == 200
    orders = pickup.json()["orders"]
    ready_codes = [o["pickup_code"] for o in orders if o["pickup_status"] == "ready"]
    assert ready_codes == ["A2", "A1"]
