"""Print job retry, waiter filtering, and job_kind classification."""

import uuid

import pytest

from app.models import LocalOrder, PrintJob
from tests.fixtures_bundles import bundle_copy, kitchen_monitor_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    return bundle_copy(kitchen_monitor_bundle())


def test_order_submit_sets_station_order_job_kind(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 3,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 20, "qty": 1, "station_uuid": "st-bar", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.station_uuid == "st-bar").one()
        assert job.job_kind == "station_order"
        assert job.status in ("queued", "sent")
    finally:
        db.close()


def test_kitchen_ticket_print_sets_kitchen_ticket_kind(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 5,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 10, "qty": 1, "station_uuid": "st-kitchen", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    ticket_id = response.json()["kitchen_ticket_ids"][0]
    print_res = c.post(f"/v1/kitchen/tickets/{ticket_id}/print")
    assert print_res.status_code == 200, print_res.text
    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.station_uuid == "st-kitchen").one()
        assert job.job_kind == "kitchen_ticket"
    finally:
        db.close()


def test_retry_failed_job(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 7,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 20, "qty": 1, "station_uuid": "st-bar", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["print_job_ids"][0]

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        job.status = "error"
        job.last_error = "connection refused"
        db.commit()
    finally:
        db.close()

    retry = c.post(f"/v1/print-jobs/{job_id}/retry")
    assert retry.status_code == 200, retry.text
    body = retry.json()
    assert body["ok"] is True
    assert body["print_job_id"] == job_id
    assert body["status"] == "queued"

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.status == "queued"
        assert job.last_error is None
    finally:
        db.close()


def test_retry_rejects_non_error_status(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 8,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 20, "qty": 1, "station_uuid": "st-bar", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["print_job_ids"][0]

    retry = c.post(f"/v1/print-jobs/{job_id}/retry")
    assert retry.status_code == 409, retry.text


def test_list_failed_jobs_for_waiter(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 9,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 20, "qty": 1, "station_uuid": "st-bar", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["print_job_ids"][0]

    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        job.status = "error"
        job.last_error = "timeout"
        db.commit()
    finally:
        db.close()

    listed = c.get(
        "/v1/print-jobs",
        params={
            "status": "error",
            "waiter_uuid": "w-1",
            "event_id": 1,
        },
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == job_id
    assert rows[0]["status"] == "error"
    assert rows[0]["station_name"] == "Bar"
    assert rows[0]["table_number"] == 9
    assert rows[0]["job_kind"] == "station_order"


def test_get_print_job_by_id(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 2,
            "waiter_uuid": "w-1",
            "lines": [
                {"article_id": 20, "qty": 1, "station_uuid": "st-bar", "note": "", "additions": []},
            ],
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["print_job_ids"][0]

    got = c.get(f"/v1/print-jobs/{job_id}")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["id"] == job_id
    assert body["station_uuid"] == "st-bar"
    assert body["event_id"] == 1
