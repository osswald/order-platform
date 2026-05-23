"""Kitchen monitor ticketing and print-on-ready behavior."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import KitchenTicket, KitchenTicketLine, PrintJob, SyncedBundle


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
                    "event_waiters": [{"uuid": "w-1", "name": "Anna"}],
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


def test_monitored_station_defers_print_until_kitchen_action(client):
    c, Session = client
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 5,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 10, "qty": 2, "station_uuid": "st-kitchen", "note": "", "additions": []},
                {"article_id": 20, "qty": 1, "station_uuid": "st-bar", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["print_job_ids"]) == 1
    assert len(body["kitchen_ticket_ids"]) == 1

    db = Session()
    try:
        assert db.query(PrintJob).filter(PrintJob.station_uuid == "st-bar").count() == 1
        assert db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").count() == 0
        ticket = db.query(KitchenTicket).one()
        line = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).one()
        assert ticket.status == "open"
        assert line.qty_total == 2
        assert line.qty_printed == 0
    finally:
        db.close()

    stations = c.get("/v1/kitchen/stations", params={"event_id": 1})
    assert stations.status_code == 200
    assert stations.json()["stations"] == [{"uuid": "st-kitchen", "name": "Grill", "sort_order": 0}]

    orders = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    assert orders.status_code == 200
    ticket_body = orders.json()["orders"][0]
    ticket_id = ticket_body["id"]
    line_id = ticket_body["lines"][0]["id"]
    assert ticket_body["lines"][0]["qty_remaining"] == 2

    one = c.post(f"/v1/kitchen/tickets/{ticket_id}/lines/{line_id}/print-one")
    assert one.status_code == 200, one.text

    db = Session()
    try:
        ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).one()
        line = db.query(KitchenTicketLine).filter(KitchenTicketLine.id == line_id).one()
        assert ticket.status == "partial"
        assert line.qty_printed == 1
        assert db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").count() == 1
    finally:
        db.close()

    rest = c.post(f"/v1/kitchen/tickets/{ticket_id}/print")
    assert rest.status_code == 200, rest.text

    db = Session()
    try:
        ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).one()
        line = db.query(KitchenTicketLine).filter(KitchenTicketLine.id == line_id).one()
        assert ticket.status == "done"
        assert line.qty_printed == 2
        assert db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").count() == 2
    finally:
        db.close()

    empty = c.get("/v1/kitchen/orders", params={"event_id": 1, "station_uuid": "st-kitchen"})
    assert empty.status_code == 200
    assert empty.json()["orders"] == []
