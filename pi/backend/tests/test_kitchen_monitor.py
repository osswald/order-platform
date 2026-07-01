"""Kitchen monitor ticketing and print-on-ready behavior."""

import base64
import uuid

import pytest
from app.models import KitchenTicket, KitchenTicketLine, PrintJob
from tests.fixtures_bundles import bundle_copy, kitchen_monitor_bundle


def _slip_text(job: PrintJob) -> str:
    return base64.b64decode(job.escpos_payload).decode("cp858", errors="replace")

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    return bundle_copy(kitchen_monitor_bundle())


def test_monitored_station_defers_print_until_kitchen_action(client_session):
    c, Session = client_session
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
        assert ticket.printer_appliance_id == 101
        assert line.qty_total == 2
        assert line.qty_printed == 0
    finally:
        db.close()

    printers = c.get("/v1/kitchen/printers", params={"event_id": 1})
    assert printers.status_code == 200
    assert printers.json()["printers"] == [
        {"printer_appliance_id": 101, "label": "Grill", "sort_order": 0}
    ]

    stations = c.get("/v1/kitchen/stations", params={"event_id": 1})
    assert stations.status_code == 200
    assert stations.json()["stations"] == [{"uuid": "101", "name": "Grill", "sort_order": 0}]

    orders = c.get("/v1/kitchen/orders", params={"event_id": 1, "printer_appliance_id": 101})
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

    empty = c.get("/v1/kitchen/orders", params={"event_id": 1, "printer_appliance_id": 101})
    assert empty.status_code == 200
    assert empty.json()["orders"] == []


def _kitchen_ticket_from_order(c, *, qty: int = 5, article_id: int = 10):
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 12,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": article_id, "qty": qty, "station_uuid": "st-kitchen", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    orders = c.get("/v1/kitchen/orders", params={"event_id": 1, "printer_appliance_id": 101})
    assert orders.status_code == 200
    ticket_body = orders.json()["orders"][0]
    return ticket_body["id"], ticket_body["lines"][0]["id"]


def test_kitchen_partial_print_two_of_five(client_session):
    c, Session = client_session
    ticket_id, line_id = _kitchen_ticket_from_order(c, qty=5)

    partial = c.post(
        f"/v1/kitchen/tickets/{ticket_id}/print-partial",
        json={"lines": [{"line_id": line_id, "qty": 2}]},
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["ticket_status"] == "partial"

    db = Session()
    try:
        ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).one()
        line = db.query(KitchenTicketLine).filter(KitchenTicketLine.id == line_id).one()
        assert ticket.status == "partial"
        assert line.qty_printed == 2
        job = db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").one()
        text = _slip_text(job)
        assert "TEILDRUCK" in text
        assert "Noch offen" in text
        assert "3" in text
        assert "Burger" in text
    finally:
        db.close()

    orders = c.get("/v1/kitchen/orders", params={"event_id": 1, "printer_appliance_id": 101})
    assert orders.json()["orders"][0]["lines"][0]["qty_remaining"] == 3


def test_kitchen_partial_print_multi_line(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 8,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 10, "qty": 2, "station_uuid": "st-kitchen", "note": "", "additions": []},
                {"article_id": 20, "qty": 3, "station_uuid": "st-kitchen", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    orders = c.get("/v1/kitchen/orders", params={"event_id": 1, "printer_appliance_id": 101})
    ticket_body = orders.json()["orders"][0]
    ticket_id = ticket_body["id"]
    burger_line = next(row for row in ticket_body["lines"] if row["line"]["article_id"] == 10)

    partial = c.post(
        f"/v1/kitchen/tickets/{ticket_id}/print-partial",
        json={"lines": [{"line_id": burger_line["id"], "qty": 1}]},
    )
    assert partial.status_code == 200, partial.text

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").one()
        text = _slip_text(job)
        assert "TEILDRUCK" in text
        assert "Noch offen" in text
        assert "Bier" in text
        assert "Burger" in text
    finally:
        db.close()


def test_kitchen_partial_print_rejects_invalid_qty(client_session):
    c, _Session = client_session
    ticket_id, line_id = _kitchen_ticket_from_order(c, qty=2)

    bad = c.post(
        f"/v1/kitchen/tickets/{ticket_id}/print-partial",
        json={"lines": [{"line_id": line_id, "qty": 5}]},
    )
    assert bad.status_code == 400

    empty = c.post(f"/v1/kitchen/tickets/{ticket_id}/print-partial", json={"lines": []})
    assert empty.status_code == 422


def test_kitchen_complete_print_has_no_teildruck_banner(client_session):
    c, Session = client_session
    ticket_id, line_id = _kitchen_ticket_from_order(c, qty=2)

    complete = c.post(f"/v1/kitchen/tickets/{ticket_id}/print")
    assert complete.status_code == 200, complete.text

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").one()
        text = _slip_text(job)
        assert "TEILDRUCK" not in text
        assert "Noch offen" not in text
    finally:
        db.close()
