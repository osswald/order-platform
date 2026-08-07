"""In-memory load-test job: status, single-flight, concurrent minute bursts."""

from __future__ import annotations

import logging
import random
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import database
from .bundle_cache import event_from_bundle, get_bundle_dict, get_bundle_dict_raw
from .load_test_basket import generate_basket_lines
from .routers.edge_orders import create_local_order, get_order_summary, settle_order_partial
from .routers.edge_payments import payment_receipt_print_to_station
from .schemas.edge import (
    LineSelection,
    LocalOrderCreate,
    PaymentReceiptPrintBody,
    TableSettlePartialBody,
)
from .schemas.order_models import LineAdditionIn, OrderLineIn, PaymentIn

log = logging.getLogger(__name__)

RECEIPT_PRINT_PROBABILITY = 0.30
DEFAULT_BURST_INTERVAL_SECONDS = 60.0

_state_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop_requested = False


def _session() -> Session:
    return database.SessionLocal()

load_test_status: dict[str, Any] = {
    "state": "idle",  # idle | running | stopping | done | failed
    "event_id": None,
    "config": None,
    "placed": 0,
    "failed": 0,
    "receipts_printed": 0,
    "current_burst": 0,
    "total_bursts": 0,
    "last_error": None,
    "started_at": None,
    "finished_at": None,
}


def reset_load_test_state_for_tests() -> None:
    """Reset module state between tests."""
    global _thread, _stop_requested
    _stop_requested = True
    if _thread is not None and _thread.is_alive():
        _thread.join(timeout=5.0)
    _thread = None
    _stop_requested = False
    with _state_lock:
        load_test_status.clear()
        load_test_status.update(
            {
                "state": "idle",
                "event_id": None,
                "config": None,
                "placed": 0,
                "failed": 0,
                "receipts_printed": 0,
                "current_burst": 0,
                "total_bursts": 0,
                "last_error": None,
                "started_at": None,
                "finished_at": None,
            }
        )


def get_status() -> dict[str, Any]:
    return deepcopy(load_test_status)


def _event_status(event: dict[str, Any] | None) -> str:
    return str((event or {}).get("status") or "").lower()


def _sorted_waiters(event: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = event.get("configuration") or {}
    waiters = list(cfg.get("event_waiters") or cfg.get("waiters") or [])
    return sorted(
        [w for w in waiters if isinstance(w, dict) and str(w.get("uuid") or "").strip()],
        key=lambda w: (str(w.get("name") or ""), str(w.get("uuid") or "")),
    )


def _sorted_registers(event: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = event.get("configuration") or {}
    regs = list(cfg.get("cash_registers") or [])
    return sorted(
        [r for r in regs if isinstance(r, dict) and str(r.get("uuid") or "").strip()],
        key=lambda r: (
            int(r.get("sort_order") or 0),
            str(r.get("name") or ""),
            str(r.get("uuid") or ""),
        ),
    )


def resolve_effective_config(
    event: dict[str, Any],
    *,
    waiter_count: int,
    cash_register_count: int,
    table_min: int,
    table_max: int,
    total_orders: int,
) -> dict[str, Any]:
    waiters = _sorted_waiters(event)
    registers = _sorted_registers(event)
    w = max(0, min(int(waiter_count), len(waiters)))
    r = max(0, min(int(cash_register_count), len(registers)))
    if w + r <= 0:
        raise HTTPException(
            status_code=400,
            detail="Need at least one waiter or cash register on the event",
        )
    if table_min < 1 or table_max < table_min:
        raise HTTPException(status_code=400, detail="Invalid table range")
    if total_orders < 1:
        raise HTTPException(status_code=400, detail="total_orders must be >= 1")
    return {
        "waiter_count": w,
        "cash_register_count": r,
        "table_min": int(table_min),
        "table_max": int(table_max),
        "total_orders": int(total_orders),
        "waiter_uuids": [str(x["uuid"]) for x in waiters[:w]],
        "cash_register_uuids": [str(x["uuid"]) for x in registers[:r]],
        "actors_per_burst": w + r,
    }


def _receipt_target(event: dict[str, Any], *, register_uuid: str | None) -> str | None:
    hosts = event.get("printer_hosts") or {}
    if register_uuid and register_uuid in hosts:
        return register_uuid
    for key in hosts:
        if str(key).startswith("appliance:"):
            continue
        return str(key)
    return None


def _client_order_id(rng: random.Random) -> str:
    return f"load-{rng.randrange(10**12):012d}"[:64]


def place_one_order(
    db: Session,
    *,
    event: dict[str, Any],
    event_id: int,
    actor_kind: str,
    actor_uuid: str,
    table_number: int | None,
    rng: random.Random,
    receipt_probability: float = RECEIPT_PRINT_PROBABILITY,
) -> dict[str, Any]:
    """Create + cash-settle one synthetic order. Returns {placed, receipt_printed}."""
    lines_raw = generate_basket_lines(event, rng=rng)
    lines = [
        OrderLineIn(
            article_id=int(line["article_id"]),
            qty=int(line["qty"]),
            note=str(line.get("note") or ""),
            additions=[
                LineAdditionIn(article_id=int(a["article_id"]), qty=int(a.get("qty") or 1))
                for a in (line.get("additions") or [])
            ],
        )
        for line in lines_raw
    ]
    if actor_kind == "waiter":
        body = LocalOrderCreate(
            client_order_id=_client_order_id(rng),
            event_id=event_id,
            table_number=int(table_number or 1),
            waiter_uuid=actor_uuid,
            order_source="waiter",
            lines=lines,
            payments=[],
        )
    else:
        body = LocalOrderCreate(
            client_order_id=_client_order_id(rng),
            event_id=event_id,
            table_number=None,
            waiter_uuid=None,
            order_source="cash_register",
            cash_register_uuid=actor_uuid,
            lines=lines,
            payments=[],
        )

    created = create_local_order(body, db=db)
    summary = get_order_summary(created.local_order_id, db=db)
    selections = [
        LineSelection(
            kind="article" if (g.kind or "article") != "voucher_sale" else "voucher_sale",
            article_id=g.article_id,
            voucher_definition_uuid=g.voucher_definition_uuid,
            qty=g.total_qty,
            note=g.note or "",
            additions=list(g.additions or []),
            discount=g.discount,
        )
        for g in summary.line_groups
        if (g.kind or "article") != "voucher_sale" or g.voucher_definition_uuid
    ]
    # Prefer article lines only for synthetic settle
    selections = [s for s in selections if s.kind == "article" and s.article_id is not None]
    if not selections:
        raise HTTPException(status_code=400, detail="No settleable lines in synthetic order")

    settle = settle_order_partial(
        created.local_order_id,
        TableSettlePartialBody(
            event_id=event_id,
            selections=selections,
            payments=[PaymentIn(type="cash", amount_cents=int(summary.total_cents))],
        ),
        db=db,
    )

    receipt_printed = False
    if settle.payment_id and rng.random() < receipt_probability:
        target = _receipt_target(
            event,
            register_uuid=actor_uuid if actor_kind == "register" else None,
        )
        if target:
            try:
                payment_receipt_print_to_station(
                    settle.payment_id,
                    PaymentReceiptPrintBody(station_uuid=target),
                    db=db,
                )
                receipt_printed = True
            except HTTPException:
                pass

    return {
        "local_order_id": created.local_order_id,
        "payment_id": settle.payment_id,
        "receipt_printed": receipt_printed,
        "order_source": actor_kind,
    }


def _place_one_order_in_thread(**kwargs: Any) -> dict[str, Any]:
    db = _session()
    try:
        return place_one_order(db, **kwargs)
    finally:
        db.close()


def _load_event(db: Session, event_id: int) -> dict[str, Any]:
    bundle = get_bundle_dict(db)
    event = event_from_bundle(bundle, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found in bundle")
    return event


def _job_loop(
    *,
    event_id: int,
    config: dict[str, Any],
    burst_interval_seconds: float,
    rng_seed: int | None,
) -> None:
    global _stop_requested
    rng = random.Random(rng_seed)
    actors: list[tuple[str, str]] = [("waiter", u) for u in config["waiter_uuids"]] + [
        ("register", u) for u in config["cash_register_uuids"]
    ]
    per_burst = len(actors)
    total = int(config["total_orders"])
    total_bursts = (total + per_burst - 1) // per_burst if per_burst else 0
    load_test_status["total_bursts"] = total_bursts
    load_test_status["started_at"] = datetime.now(UTC).isoformat()
    started_mono = time.monotonic()
    placed_target_remaining = total
    burst_index = 0

    try:
        while placed_target_remaining > 0:
            if _stop_requested:
                load_test_status["state"] = "stopping"
                break

            db = _session()
            try:
                bundle = get_bundle_dict_raw(db)
                event = event_from_bundle(bundle or {}, event_id) if bundle else None
                if _event_status(event) != "test":
                    load_test_status["state"] = "failed"
                    load_test_status["last_error"] = "Event is no longer in test status"
                    break
                assert event is not None
                event_snapshot = deepcopy(event)
            finally:
                db.close()

            burst_index += 1
            load_test_status["current_burst"] = burst_index
            load_test_status["state"] = "running"

            burst_count = min(per_burst, placed_target_remaining)
            burst_actors = actors[:burst_count]
            futures = []
            with ThreadPoolExecutor(max_workers=max(1, burst_count)) as pool:
                for kind, uuid in burst_actors:
                    table = None
                    if kind == "waiter":
                        table = rng.randint(int(config["table_min"]), int(config["table_max"]))
                    actor_rng = random.Random(rng.random())
                    futures.append(
                        pool.submit(
                            _place_one_order_in_thread,
                            event=event_snapshot,
                            event_id=event_id,
                            actor_kind=kind,
                            actor_uuid=uuid,
                            table_number=table,
                            rng=actor_rng,
                        )
                    )
                for fut in as_completed(futures):
                    placed_target_remaining -= 1
                    try:
                        result = fut.result()
                    except Exception as exc:
                        load_test_status["failed"] = int(load_test_status["failed"]) + 1
                        load_test_status["last_error"] = str(exc)[:500]
                        log.warning("Load-test actor failed: %s", exc)
                        continue
                    load_test_status["placed"] = int(load_test_status["placed"]) + 1
                    if result.get("receipt_printed"):
                        load_test_status["receipts_printed"] = int(load_test_status["receipts_printed"]) + 1

            if _stop_requested or placed_target_remaining <= 0:
                break

            next_at = started_mono + burst_index * burst_interval_seconds
            while time.monotonic() < next_at:
                if _stop_requested:
                    break
                time.sleep(min(0.1, next_at - time.monotonic()))

        if load_test_status["state"] not in ("failed",):
            load_test_status["state"] = "done"
    except Exception as exc:
        load_test_status["state"] = "failed"
        load_test_status["last_error"] = f"{exc}\n{traceback.format_exc()}"[:2000]
        log.exception("Load-test job failed")
    finally:
        load_test_status["finished_at"] = datetime.now(UTC).isoformat()
        if load_test_status["state"] == "stopping":
            load_test_status["state"] = "done"
        _stop_requested = False


def start_load_test(
    *,
    event_id: int,
    waiter_count: int,
    cash_register_count: int,
    table_min: int,
    table_max: int,
    total_orders: int,
    burst_interval_seconds: float = DEFAULT_BURST_INTERVAL_SECONDS,
    rng_seed: int | None = None,
) -> dict[str, Any]:
    global _thread, _stop_requested
    with _state_lock:
        if load_test_status["state"] in ("running", "stopping") or (
            _thread is not None and _thread.is_alive()
        ):
            raise HTTPException(status_code=409, detail="Load-test already running")

        db = _session()
        try:
            event = _load_event(db, event_id)
            if _event_status(event) != "test":
                raise HTTPException(status_code=409, detail="Load-test only allowed for test events")
            config = resolve_effective_config(
                event,
                waiter_count=waiter_count,
                cash_register_count=cash_register_count,
                table_min=table_min,
                table_max=table_max,
                total_orders=total_orders,
            )
        finally:
            db.close()

        _stop_requested = False
        load_test_status.update(
            {
                "state": "running",
                "event_id": event_id,
                "config": config,
                "placed": 0,
                "failed": 0,
                "receipts_printed": 0,
                "current_burst": 0,
                "total_bursts": 0,
                "last_error": None,
                "started_at": None,
                "finished_at": None,
            }
        )
        _thread = threading.Thread(
            target=_job_loop,
            kwargs={
                "event_id": event_id,
                "config": config,
                "burst_interval_seconds": burst_interval_seconds,
                "rng_seed": rng_seed,
            },
            name="pi-load-test",
            daemon=True,
        )
        _thread.start()
        return get_status()


def stop_load_test() -> dict[str, Any]:
    global _stop_requested
    with _state_lock:
        if load_test_status["state"] not in ("running", "stopping"):
            return get_status()
        _stop_requested = True
        load_test_status["state"] = "stopping"
        return get_status()


def wait_until_idle_for_tests(timeout: float = 10.0) -> dict[str, Any]:
    """Poll until job leaves running/stopping (tests only)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        st = get_status()
        if st["state"] not in ("running", "stopping"):
            return st
        time.sleep(0.05)
    return get_status()
