"""Print worker wake-on-enqueue, off-loop render, and hot-path indexes."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from unittest.mock import AsyncMock

from app.models import LocalOrder, PrintJob
from app.models_operational import OrderSession
from app.print_render import dump_render_context, make_render_context
from app.print_worker import (
    PRINT_WORKER_IDLE_TIMEOUT_SECONDS,
    notify_print_worker,
    print_worker_loop,
    process_print_job,
)
from sqlalchemy import inspect
from tests.fixtures_bundles import default_bundle


def _seed_order_and_job(db, *, with_payload: bool = False) -> PrintJob:
    bundle = default_bundle()
    from app.models import SyncedBundle

    if not db.query(SyncedBundle).filter(SyncedBundle.id == 1).first():
        db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    session = OrderSession(event_id=1, table_number=1)
    db.add(session)
    db.flush()
    order = LocalOrder(
        session_id=session.id,
        event_id=1,
        client_order_id=f"co-{time.time_ns()}",
        table_number=1,
        payment_status="open",
        print_status="pending",
        payload_json=json.dumps(
            {
                "lines": [{"article_id": 10, "qty": 1}],
                "event_id": 1,
            }
        ),
    )
    db.add(order)
    db.flush()
    ctx = make_render_context(
        kind="station_order",
        event_id=1,
        event_name="Test",
        currency="CHF",
        feed_lines=1,
        station_name="Bar",
        local_order_id=order.id,
        payload={"lines": [{"article_id": 10, "qty": 1}], "event_id": 1},
    )
    job = PrintJob(
        local_order_id=order.id,
        station_uuid="st-1",
        job_kind="station_order",
        printer_host="127.0.0.1",
        printer_port=9100,
        escpos_payload=base64.b64encode(b"PREBUILT").decode("ascii") if with_payload else "",
        render_context_json=None if with_payload else dump_render_context(ctx),
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_notify_wakes_idle_print_worker(monkeypatch, isolated_engine, db_session):
    monkeypatch.setattr("app.print_worker.PRINT_WORKER_IDLE_TIMEOUT_SECONDS", 30.0)
    monkeypatch.setattr(
        "app.print_worker._send_to_printer",
        AsyncMock(return_value=None),
    )

    async def _run() -> float:
        stop = asyncio.Event()
        worker = asyncio.create_task(print_worker_loop(stop))
        await asyncio.sleep(0.05)
        started = time.monotonic()
        job = _seed_order_and_job(db_session, with_payload=True)
        notify_print_worker()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            db_session.expire_all()
            row = db_session.query(PrintJob).filter(PrintJob.id == job.id).first()
            if row and row.status == "sent":
                break
            await asyncio.sleep(0.05)
        else:
            stop.set()
            await worker
            raise AssertionError("print job was not processed after wake")
        elapsed = time.monotonic() - started
        stop.set()
        await worker
        return elapsed

    elapsed = asyncio.run(_run())
    assert elapsed < 5.0, f"wake path too slow ({elapsed:.2f}s); likely waited on idle poll only"


def test_process_print_job_uses_to_thread_for_deferred_render(
    monkeypatch, isolated_engine, db_session
):
    monkeypatch.setattr(
        "app.print_worker._send_to_printer",
        AsyncMock(return_value=None),
    )
    calls: list[str] = []
    real_to_thread = asyncio.to_thread

    async def tracking_to_thread(fn, /, *args, **kwargs):
        calls.append(getattr(fn, "__name__", str(fn)))
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr("app.print_worker.asyncio.to_thread", tracking_to_thread)

    job = _seed_order_and_job(db_session, with_payload=False)

    async def _run():
        await process_print_job(db_session, job, default_bundle()["events"][0])
        db_session.commit()

    asyncio.run(_run())
    assert "build_escpos_from_render_context" in calls
    assert job.status == "sent"
    assert job.escpos_payload


def test_process_print_job_render_failure_marks_error(monkeypatch, isolated_engine, db_session):
    def boom(*_a, **_k):
        raise ValueError("boom")

    monkeypatch.setattr("app.print_render.build_escpos_from_render_context", boom)
    job = _seed_order_and_job(db_session, with_payload=False)

    async def _run():
        await process_print_job(db_session, job, default_bundle()["events"][0])
        db_session.commit()

    asyncio.run(_run())
    assert job.status == "error"
    assert "boom" in (job.last_error or "")


def test_hot_path_indexes_exist_on_test_schema(isolated_engine):
    inspector = inspect(isolated_engine)

    def names(table: str) -> set[str]:
        return {ix["name"] for ix in inspector.get_indexes(table)}

    assert "ix_print_jobs_status" in names("print_jobs")
    assert "ix_order_submissions_event_payment" in names("order_submissions")
    assert "ix_sync_outbox_status" in names("sync_outbox")
    assert "ix_kitchen_tickets_event_status" in names("kitchen_tickets")


def test_alembic_head_is_hot_path_indexes():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    head = ScriptDirectory.from_config(cfg).get_current_head()
    assert head == "008_hot_path_indexes"


def test_idle_timeout_default_is_bounded():
    assert 0.2 <= float(PRINT_WORKER_IDLE_TIMEOUT_SECONDS) <= 5.0
