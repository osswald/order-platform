"""Deferred PrintJob render + logo cache integration on order create."""

from __future__ import annotations

import base64
import json
import uuid

import pytest
from app.escpos_render import clear_receipt_logo_cache
from app.models import PrintJob
from app.print_render import ensure_print_job_payload
from app.print_worker import run_print_job_sync
from tests.fixtures_bundles import bundle_copy, kitchen_monitor_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture(autouse=True)
def _clear_logo_cache():
    clear_receipt_logo_cache()
    yield
    clear_receipt_logo_cache()


@pytest.fixture
def bundle():
    return bundle_copy(kitchen_monitor_bundle())


def test_order_create_stores_render_context_for_station_job(client_session):
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
    job_id = response.json()["print_job_ids"][0]
    db = Session()
    try:
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.render_context_json
        ctx = json.loads(job.render_context_json)
        assert ctx["v"] == 1
        assert ctx["kind"] == "station_order"
        assert ctx["payload"]["lines"]
        # Worker may race and fill payload; clear to prove context alone renders.
        job.escpos_payload = ""
        job.status = "queued"
        raw = ensure_print_job_payload(db, job)
        assert len(raw) > 20
        assert job.escpos_payload
        db.commit()
    finally:
        db.close()


def test_print_worker_renders_then_sends_deferred_job(client_session, mock_printer_tcp):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 4,
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
        assert job.render_context_json
        job.escpos_payload = ""
        job.status = "queued"
        job.last_error = None
        db.commit()
        before = len(mock_printer_tcp)
        run_print_job_sync(db, job_id)
        db.commit()
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.status == "sent"
        assert job.escpos_payload
        assert base64.b64decode(job.escpos_payload)
        assert len(mock_printer_tcp) == before + 1
    finally:
        db.close()


def test_render_failure_marks_job_error(client_session):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 5,
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
        job.escpos_payload = ""
        job.render_context_json = json.dumps({"v": 1, "kind": "station_order", "event_id": 1})
        job.status = "queued"
        job.last_error = None
        db.commit()
        run_print_job_sync(db, job_id)
        db.commit()
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.status == "error"
        assert job.last_error
    finally:
        db.close()


def test_legacy_prefilled_payload_still_sends(client_session, mock_printer_tcp):
    c, Session = client_session
    response = c.post(
        "/v1/orders",
        json={
            "client_order_id": f"pwa-{uuid.uuid4().hex[:12]}",
            "event_id": 1,
            "table_number": 6,
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
        # Simulate legacy row: pre-built payload, no context.
        job.escpos_payload = base64.b64encode(b"\x1b@legacy").decode("ascii")
        job.render_context_json = None
        job.status = "queued"
        job.last_error = None
        db.commit()
        before = len(mock_printer_tcp)
        run_print_job_sync(db, job_id)
        db.commit()
        job = db.query(PrintJob).filter(PrintJob.id == job_id).one()
        assert job.status == "sent"
        assert len(mock_printer_tcp) == before + 1
    finally:
        db.close()