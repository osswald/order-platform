import base64
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..cloud_client import CloudConfigError
from ..sync_service import (
    is_cloud_configured,
    pending_outbox_count,
    pull_bundle,
    push_outbox,
    reapply_pending_stock,
    sync_status,
)
from ..database import SessionLocal
from ..models import LocalOrder, OutboxEntry, PrintJob, SyncedBundle
from ..security import verify_password
from ..print_worker import (
    build_escpos_receipt_text,
    group_lines_by_station,
    resolve_station_uuid_for_line,
    station_name_from_event,
    _article_map as _print_article_map,
)
from ..pricing import line_total_cents, line_unit_cents
from ..stock import apply_stock_to_bundle, save_bundle, validate_stock

router = APIRouter()

PAYMENT_MODES_CASH = {"pay_now", "instant"}
ALLOWED_PAYMENT_TYPES = frozenset({"cash", "twint", "sumup"})


def _event_payment_types(ev: dict) -> set[str]:
    raw = ev.get("payment_types")
    if isinstance(raw, list) and raw:
        out = {str(t).strip().lower() for t in raw if str(t).strip().lower() in ALLOWED_PAYMENT_TYPES}
        if out:
            return out
    return {"cash"}


def _lines_with_station_uuid(ev: dict, lines: list) -> list:
    out = []
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        ln = dict(line)
        if not ln.get("station_uuid"):
            su = resolve_station_uuid_for_line(ev, ln)
            if su:
                ln["station_uuid"] = su
        out.append(ln)
    return out


def _validate_payment_types(ev: dict, payments: list) -> None:
    if not payments:
        return
    allowed = _event_payment_types(ev)
    pm = (ev.get("payment_mode") or "pay_later").lower()
    for p in payments:
        if not isinstance(p, dict):
            continue
        t = (p.get("type") or "").strip().lower()
        if t == "instant" and pm == "instant":
            continue
        if t not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Payment type «{t or '?'}» is not allowed for this event",
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_bundle_dict(db: Session) -> dict:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        raise HTTPException(status_code=400, detail="No bundle; run POST /v1/sync/pull first")
    data = json.loads(row.json_body)
    if not isinstance(data, dict) or data.get("organisation_id") is None:
        raise HTTPException(status_code=400, detail="No bundle; run POST /v1/sync/pull first")
    return data


def _event_from_bundle(bundle: dict, event_id: int) -> dict | None:
    for ev in bundle.get("events", []) or []:
        if int(ev["id"]) == int(event_id):
            return ev
    return None


def _article_map(ev: dict) -> dict:
    return ev.get("articles") or {}


def _line_totals(lines: list, articles: dict) -> tuple[int, int]:
    total_cents = 0
    item_count = 0
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        qty = max(1, int(line.get("qty") or 1))
        total_cents += line_total_cents(line, articles)
        item_count += qty
    return total_cents, item_count


def _payment_status_for_create(ev: dict, payments: list) -> str:
    pm = (ev.get("payment_mode") or "pay_later").lower()
    if pm == "instant":
        return "paid"
    if pm in PAYMENT_MODES_CASH and payments:
        return "paid"
    return "open"


def _normalize_additions(additions: list | None) -> list[dict]:
    out = []
    for add in additions or []:
        if not isinstance(add, dict):
            continue
        aid = add.get("article_id")
        if aid is None:
            continue
        out.append({"article_id": int(aid), "qty": max(1, int(add.get("qty") or 1))})
    return out


def _additions_signature(additions: list | None) -> str:
    items = _normalize_additions(additions)
    items.sort(key=lambda x: (x["article_id"], x["qty"]))
    return json.dumps(items, separators=(",", ":"))


def _line_key(article_id, note: str, additions: list | None = None) -> tuple[int, str, str]:
    return (int(article_id), str(note or ""), _additions_signature(additions))


def _unit_cents_for_article(
    articles: dict,
    article_id,
    note: str = "",
    additions: list | None = None,
) -> int:
    line = {"article_id": article_id, "qty": 1, "note": note, "additions": _normalize_additions(additions)}
    return line_unit_cents(line, articles)


def _selections_total_cents(selections: list, articles: dict) -> int:
    total = 0
    for s in selections:
        if not isinstance(s, dict):
            continue
        qty = max(1, int(s.get("qty") or 1))
        total += (
            _unit_cents_for_article(
                articles,
                s.get("article_id"),
                s.get("note", ""),
                s.get("additions"),
            )
            * qty
        )
    return total


def _build_line_groups_from_orders(orders: list, articles: dict) -> list[dict]:
    merged: dict[tuple[int, str, str], dict] = {}
    for o in orders:
        payload = json.loads(o.payload_json)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            aid = line.get("article_id")
            if aid is None:
                continue
            note = str(line.get("note") or "")
            adds = _normalize_additions(line.get("additions"))
            key = _line_key(aid, note, adds)
            qty = max(1, int(line.get("qty") or 1))
            line_cents = line_total_cents(line, articles)
            unit = line_unit_cents(line, articles)
            if key not in merged:
                merged[key] = {
                    "article_id": int(aid),
                    "note": note,
                    "additions": adds,
                    "total_qty": 0,
                    "unit_cents": unit,
                    "line_total_cents": 0,
                }
            merged[key]["total_qty"] += qty
            merged[key]["line_total_cents"] += line_cents
    return sorted(merged.values(), key=lambda g: (g["article_id"], g["note"], _additions_signature(g.get("additions"))))


def _resolve_printer(ev: dict, station_uuid: str | None) -> tuple[str, int]:
    hosts = ev.get("printer_hosts") or {}
    key = str(station_uuid) if station_uuid is not None else None
    if key and key in hosts:
        h, _, p = hosts[key].partition(":")
        return h, int(p or 9100)
    if hosts:
        first = next(iter(hosts.values()))
        h, _, p = first.partition(":")
        return h, int(p or 9100)
    h = os.getenv("DEFAULT_PRINTER_HOST", "192.168.192.11")
    return h, int(os.getenv("DEFAULT_PRINTER_PORT", "9100"))


def _sync_outbox_payload(db: Session, order: LocalOrder, payload: dict) -> None:
    out = db.query(OutboxEntry).filter(OutboxEntry.client_order_id == order.client_order_id).first()
    if out and out.status == "pending":
        out.payload_json = json.dumps(payload)


def _cloud_config_http_error(e: CloudConfigError) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "message": "Pi backend is not configured for cloud sync. Set variables in pi/.env and restart the container.",
            "missing": e.missing,
        },
    )


@router.get("/v1/sync/status")
def get_sync_status(db: Session = Depends(get_db)):
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    last_sync_at = row.updated_at.isoformat() if row and row.updated_at else None
    return {
        **sync_status,
        "configured": is_cloud_configured(),
        "pending_outbox_count": pending_outbox_count(db),
        "bundle_last_sync_at": last_sync_at,
    }


@router.post("/v1/sync/pull")
async def sync_pull(db: Session = Depends(get_db)):
    try:
        result = await pull_bundle(db)
        reapply_pending_stock(db, result.get("bundle"))
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e
    return {"ok": True, "event_count": result["event_count"]}


@router.get("/v1/bundle")
def get_bundle(db: Session = Depends(get_db)):
    return _get_bundle_dict(db)


@router.get("/v1/meta")
def get_meta(db: Session = Depends(get_db)):
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row:
        return {"last_sync_at": None}
    return {"last_sync_at": row.updated_at.isoformat() if row.updated_at else None}


@router.post("/v1/sync/push")
async def sync_push(db: Session = Depends(get_db)):
    try:
        return await push_outbox(db, retry_errors=False)
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e


class LocalOrderCreate(BaseModel):
    client_order_id: str = Field(..., min_length=8, max_length=64)
    event_id: int
    table_number: int = Field(..., ge=1, le=99999)
    waiter_uuid: str | None = None
    lines: list[dict] = Field(default_factory=list)
    payments: list[dict] = Field(default_factory=list)


class OrderPayBody(BaseModel):
    payments: list[dict] = Field(default_factory=list)


class TableSettleBody(BaseModel):
    event_id: int
    payments: list[dict] = Field(default_factory=list)


class LineSelection(BaseModel):
    article_id: int
    note: str = ""
    qty: int = Field(..., ge=1)
    additions: list[dict] = Field(default_factory=list)


class TableSettlePartialBody(BaseModel):
    event_id: int
    payments: list[dict] = Field(default_factory=list)
    selections: list[LineSelection] = Field(default_factory=list)


@router.post("/v1/orders")
def create_local_order(body: LocalOrderCreate, db: Session = Depends(get_db)):
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    if db.query(LocalOrder).filter(LocalOrder.client_order_id == body.client_order_id).first():
        raise HTTPException(status_code=409, detail="Duplicate client_order_id")

    line_dicts = [
        {
            "article_id": ln.get("article_id"),
            "qty": ln.get("qty"),
            "note": ln.get("note") or "",
        }
        for ln in body.lines
        if isinstance(ln, dict)
    ]
    validate_stock(ev, line_dicts)

    pm = (ev.get("payment_mode") or "pay_later").lower()
    arts = _article_map(ev)
    payments = list(body.payments or [])
    if pm == "instant":
        line_cents, _ = _line_totals(body.lines, arts)
        payments = [{"type": "instant", "amount_cents": line_cents}]

    if payments:
        _validate_payment_types(ev, payments)

    payment_status = _payment_status_for_create(ev, payments)
    order_lines = _lines_with_station_uuid(ev, body.lines)
    payload = {
        "client_order_id": body.client_order_id,
        "event_id": body.event_id,
        "table_number": body.table_number,
        "waiter_uuid": body.waiter_uuid,
        "lines": order_lines,
        "payments": payments,
        "payment_status": payment_status,
    }
    order = LocalOrder(
        client_order_id=body.client_order_id,
        event_id=body.event_id,
        table_number=body.table_number,
        waiter_uuid=body.waiter_uuid,
        payment_status=payment_status,
        payload_json=json.dumps(payload),
        print_status="pending",
    )
    db.add(order)
    db.flush()

    ev_name = ev.get("name", "Event")
    groups = group_lines_by_station(ev, order_lines)
    print_job_ids: list[int] = []

    for station_uuid, station_lines in groups.items():
        station_payload = {**payload, "lines": station_lines}
        station_label = station_name_from_event(ev, station_uuid)
        host, port = _resolve_printer(ev, station_uuid)
        esc = build_escpos_receipt_text(
            station_payload,
            ev_name,
            station_name=station_label,
            articles=arts,
        )
        pj = PrintJob(
            local_order_id=order.id,
            station_uuid=station_uuid,
            printer_host=host,
            printer_port=port,
            escpos_payload=base64.b64encode(esc).decode("ascii"),
            status="queued",
        )
        db.add(pj)
        db.flush()
        print_job_ids.append(pj.id)

    out = OutboxEntry(
        client_order_id=body.client_order_id,
        event_id=body.event_id,
        payload_json=json.dumps(payload),
        status="pending",
    )
    db.add(out)

    articles_patch = apply_stock_to_bundle(bundle, body.event_id, line_dicts)
    save_bundle(db, bundle)

    db.commit()
    return {
        "local_order_id": order.id,
        "print_job_id": print_job_ids[0] if print_job_ids else None,
        "print_job_ids": print_job_ids,
        "payment_status": payment_status,
        "payment_mode": (ev.get("payment_mode") or "pay_later").lower(),
        "articles": articles_patch,
    }


@router.post("/v1/orders/{order_id}/pay")
def pay_local_order(order_id: int, body: OrderPayBody, db: Session = Depends(get_db)):
    order = db.query(LocalOrder).filter(LocalOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, order.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    pm = (ev.get("payment_mode") or "pay_later").lower()
    if pm not in PAYMENT_MODES_CASH:
        raise HTTPException(status_code=400, detail="Event does not require immediate payment")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")

    _validate_payment_types(ev, body.payments)

    payload = json.loads(order.payload_json)
    payload["payments"] = body.payments
    payload["payment_status"] = "paid"
    order.payment_status = "paid"
    order.payload_json = json.dumps(payload)
    _sync_outbox_payload(db, order, payload)
    db.commit()
    return {"local_order_id": order.id, "payment_status": "paid"}


@router.get("/v1/tables/open")
def list_open_tables(event_id: int = Query(...), db: Session = Depends(get_db)):
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    arts = _article_map(ev)
    currency = ev.get("currency", "EUR")
    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.payment_status == "open",
            LocalOrder.table_number.isnot(None),
        )
        .order_by(LocalOrder.table_number.asc(), LocalOrder.id.asc())
        .all()
    )

    by_table: dict[int, dict] = {}
    for o in orders:
        tn = int(o.table_number)
        if tn not in by_table:
            by_table[tn] = {"table_number": tn, "order_count": 0, "total_cents": 0, "item_count": 0}
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        line_cents, line_qty = _line_totals(lines, arts)
        by_table[tn]["order_count"] += 1
        by_table[tn]["total_cents"] += line_cents
        by_table[tn]["item_count"] += line_qty

    tables = [
        {**row, "currency": currency}
        for row in sorted(by_table.values(), key=lambda r: r["table_number"])
    ]
    return {"event_id": event_id, "currency": currency, "tables": tables}


@router.get("/v1/tables/{table_number}")
def get_table_summary(
    table_number: int,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if table_number < 1 or table_number > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")

    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    arts = _article_map(ev)
    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )

    open_orders = []
    aggregated_lines = []
    total_cents = 0
    item_count = 0

    for o in orders:
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        line_cents, line_qty = _line_totals(lines, arts)
        total_cents += line_cents
        item_count += line_qty
        open_orders.append(
            {
                "local_order_id": o.id,
                "client_order_id": o.client_order_id,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "lines": lines,
                "line_total_cents": line_cents,
            }
        )
        for line in lines:
            if not isinstance(line, dict):
                continue
            aggregated_lines.append(
                {
                    "local_order_id": o.id,
                    "article_id": line.get("article_id"),
                    "qty": line.get("qty", 1),
                    "note": line.get("note", ""),
                    "additions": _normalize_additions(line.get("additions")),
                }
            )

    line_groups = _build_line_groups_from_orders(orders, arts)

    return {
        "table_number": table_number,
        "event_id": event_id,
        "currency": ev.get("currency", "EUR"),
        "open_orders": open_orders,
        "aggregated_lines": aggregated_lines,
        "line_groups": line_groups,
        "total_cents": total_cents,
        "item_count": item_count,
    }


@router.post("/v1/tables/{table_number}/settle-partial")
def settle_table_partial(table_number: int, body: TableSettlePartialBody, db: Session = Depends(get_db)):
    if table_number < 1 or table_number > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")

    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")

    _validate_payment_types(ev, body.payments)

    arts = _article_map(ev)
    selections = [s.model_dump() for s in body.selections]
    expected_cents = _selections_total_cents(selections, arts)
    paid_total = sum(int(p.get("amount_cents") or 0) for p in body.payments if isinstance(p, dict))
    if paid_total != expected_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match selection total {expected_cents}",
        )

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    need: dict[tuple[int, str, str], int] = {}
    for s in selections:
        key = _line_key(s["article_id"], s.get("note", ""), s.get("additions"))
        need[key] = need.get(key, 0) + int(s["qty"])

    paid_lines: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for order in orders:
        payload = json.loads(order.payload_json)
        open_lines: list[dict] = []
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            aid = line.get("article_id")
            if aid is None:
                continue
            note = str(line.get("note") or "")
            adds = _normalize_additions(line.get("additions"))
            key = _line_key(aid, note, adds)
            qty = max(1, int(line.get("qty") or 1))
            take = min(qty, need.get(key, 0))
            if take > 0:
                pl = {
                    "article_id": int(aid),
                    "qty": take,
                    "note": note,
                    "additions": adds,
                }
                su = line.get("station_uuid")
                if su:
                    pl["station_uuid"] = su
                paid_lines.append(pl)
                need[key] = need.get(key, 0) - take
                qty -= take
            if qty > 0:
                rem = {**line, "qty": qty, "additions": adds}
                open_lines.append(rem)
        payload["lines"] = open_lines
        if open_lines:
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)
        else:
            order.payment_status = "paid"
            payload["payment_status"] = "paid"
            payload["settled_at"] = now
            payload["settlement_table"] = table_number
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)

    leftover = sum(v for v in need.values() if v > 0)
    if leftover > 0:
        raise HTTPException(status_code=400, detail="Selection exceeds open quantities on table")

    paid_order_ids: list[int] = []
    if paid_lines:
        pay_cid = f"partial-{table_number}-{uuid.uuid4().hex[:12]}"
        paid_lines = _lines_with_station_uuid(ev, paid_lines)
        paid_payload = {
            "client_order_id": pay_cid,
            "event_id": body.event_id,
            "table_number": table_number,
            "waiter_uuid": orders[0].waiter_uuid if orders else None,
            "lines": paid_lines,
            "payments": body.payments,
            "payment_status": "paid",
            "settled_at": now,
            "settlement_table": table_number,
            "partial_settlement": True,
        }
        paid_order = LocalOrder(
            client_order_id=pay_cid,
            event_id=body.event_id,
            table_number=table_number,
            waiter_uuid=orders[0].waiter_uuid if orders else None,
            payment_status="paid",
            payload_json=json.dumps(paid_payload),
            print_status="done",
        )
        db.add(paid_order)
        db.flush()
        paid_order_ids.append(paid_order.id)
        db.add(
            OutboxEntry(
                client_order_id=pay_cid,
                event_id=body.event_id,
                payload_json=json.dumps(paid_payload),
                status="pending",
            )
        )

    db.commit()

    remaining_orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    remaining_cents = 0
    for o in remaining_orders:
        payload = json.loads(o.payload_json)
        cents, _ = _line_totals(payload.get("lines") or [], arts)
        remaining_cents += cents

    return {
        "paid_cents": expected_cents,
        "remaining_cents": remaining_cents,
        "paid_order_ids": paid_order_ids,
        "table_number": table_number,
    }


@router.post("/v1/tables/{table_number}/settle")
def settle_table(table_number: int, body: TableSettleBody, db: Session = Depends(get_db)):
    if table_number < 1 or table_number > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")

    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")

    _validate_payment_types(ev, body.payments)

    now = datetime.now(timezone.utc).isoformat()
    paid_ids = []
    arts = _article_map(ev)
    total_cents = 0
    for o in orders:
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        cents, _ = _line_totals(lines, arts)
        total_cents += cents

    paid_total = sum(int(p.get("amount_cents") or 0) for p in body.payments if isinstance(p, dict))
    if paid_total != total_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match open balance {total_cents}",
        )

    for o in orders:
        payload = json.loads(o.payload_json)
        payload["payments"] = body.payments
        payload["payment_status"] = "paid"
        payload["settled_at"] = now
        payload["settlement_table"] = table_number
        o.payment_status = "paid"
        o.payload_json = json.dumps(payload)
        _sync_outbox_payload(db, o, payload)
        paid_ids.append(o.id)

    db.commit()
    return {"paid_order_ids": paid_ids, "total_cents": total_cents, "table_number": table_number}


def _bundle_dict_optional(db: Session) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    if not isinstance(data, dict) or data.get("organisation_id") is None:
        return None
    return data


@router.get("/v1/admin/status")
def admin_status(db: Session = Depends(get_db)):
    bundle = _bundle_dict_optional(db)
    bundle_ready = bundle is not None
    hashes = (bundle or {}).get("admin_pin_hashes") or []
    return {
        "bundle_ready": bundle_ready,
        "requires_pin": bundle_ready and len(hashes) > 0,
    }


class AdminVerifyBody(BaseModel):
    pin: str = Field(..., min_length=6, max_length=6)


@router.post("/v1/admin/verify")
def verify_admin_pin(body: AdminVerifyBody, db: Session = Depends(get_db)):
    if not body.pin.isdigit():
        raise HTTPException(status_code=401, detail="Invalid admin code")
    bundle = _bundle_dict_optional(db)
    if bundle is None:
        raise HTTPException(status_code=401, detail="Invalid admin code")
    hashes = bundle.get("admin_pin_hashes") or []
    if not hashes:
        raise HTTPException(status_code=401, detail="no_admin_pins_configured")
    for h in hashes:
        if h and verify_password(body.pin, h):
            return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid admin code")


@router.get("/v1/print-jobs")
def list_print_jobs(db: Session = Depends(get_db)):
    rows = db.query(PrintJob).order_by(PrintJob.id.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "local_order_id": r.local_order_id,
            "printer_host": r.printer_host,
            "status": r.status,
            "last_error": r.last_error,
        }
        for r in rows
    ]
