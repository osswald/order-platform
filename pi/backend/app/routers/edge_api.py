import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..cloud_client import (
    CloudConfigError,
    create_terminal_connection_token as cloud_create_terminal_connection_token,
    create_terminal_payment_intent as cloud_create_terminal_payment_intent,
    retrieve_terminal_payment_intent as cloud_retrieve_terminal_payment_intent,
)
from ..sync_service import (
    is_cloud_configured,
    pending_outbox_count,
    pull_bundle,
    push_outbox,
    reapply_pending_stock,
    sync_status,
)
from ..deps import get_db
from ..schemas.bundle import EdgeBundleResponse
from ..schemas.edge import (
    AccountSummaryResponse,
    AdminStatusResponse,
    AdminVerifyBody,
    AssignCollectiveBody,
    AssignCollectiveResponse,
    CollectiveBillCreatedResponse,
    CollectivePartialSettleResponse,
    CollectiveSettleResponse,
    CollectiveBillCreateBody,
    EscposPayloadResponse,
    KitchenOrdersResponse,
    KitchenStationsResponse,
    KitchenTicketPrintResponse,
    LineSelection,
    LocalOrderCreate,
    LocalOrderCreatedResponse,
    OkResponse,
    OpenCollectiveBillsResponse,
    OpenTablesResponse,
    OrderPayBody,
    OrderPayResponse,
    PaymentReceiptBody,
    PaymentReceiptEscposResponse,
    PaymentsListResponse,
    PickupOrdersResponse,
    PickupPickedUpResponse,
    PrinterTestReceiptBody,
    PrintJobSummary,
    RegisterDisplayBody,
    RegisterDisplayResponse,
    SyncMetaResponse,
    SyncPullResponse,
    SyncPushResponse,
    SyncStatusResponse,
    TablePartialSettleResponse,
    TableSettleBody,
    TableSettlePartialBody,
    TableSettleResponse,
    TransferLinesBody,
    TransferLinesResponse,
)
from ..order_line_utils import copy_line_fiscal_fields
from ..order_fiscal import (
    allocate_order_number,
    distinct_order_numbers_from_payload,
    distinct_order_numbers_for_local_orders,
    is_ferdig_client_order_id,
    snapshot_lines,
    waiter_name_from_event,
)
from ..line_moves import append_lines_to_collective, append_lines_to_table, take_from_orders
from ..models import (
    CollectiveBill,
    EventPickupCounter,
    KitchenTicket,
    KitchenTicketLine,
    LocalOrder,
    OutboxEntry,
    PaymentReceipt,
    PrintJob,
    RegisterDisplayState,
    SyncedBundle,
)
from ..security import verify_password
from ..print_worker import (
    build_customer_pickup_text,
    build_escpos_receipt_text,
    build_payment_receipt_text,
    build_voucher_slip_text,
    group_lines_by_station,
    resolve_station_uuid_for_line,
    station_name_from_event,
    _article_map as _print_article_map,
)
from ..pricing import line_total_cents, line_unit_cents
from ..stock import apply_stock_to_bundle, save_bundle, validate_stock
from ..vouchers import (
    article_lines_only,
    compute_voucher_credits,
    is_voucher_sale_line,
    order_lines_total_cents,
    voucher_definition_by_uuid,
    voucher_sale_unit_cents,
)

router = APIRouter()

PAYMENT_MODES_CASH = {"pay_now", "instant"}
ALLOWED_PAYMENT_TYPES = frozenset({"cash", "twint", "sumup", "stripe_terminal"})


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


def _line_totals(lines: list, articles: dict, ev: dict | None = None) -> tuple[int, int]:
    if ev is not None:
        return order_lines_total_cents(lines, ev, articles)
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


def _selections_total_cents_from_groups(selections: list, line_groups: list[dict]) -> int:
    """Sum selection qty using unit_cents from open order line groups (price snapshots)."""
    unit_by_key: dict[tuple[int, str, str], int] = {}
    for g in line_groups:
        key = _line_key(g["article_id"], g.get("note", ""), g.get("additions"))
        unit_by_key[key] = int(g["unit_cents"])
    total = 0
    for s in selections:
        if not isinstance(s, dict):
            continue
        qty = max(1, int(s.get("qty") or 1))
        key = _line_key(s.get("article_id"), s.get("note", ""), s.get("additions"))
        unit = unit_by_key.get(key)
        if unit is None:
            raise HTTPException(status_code=400, detail="Selection not found on open orders")
        total += unit * qty
    return total


def _build_line_groups_from_orders(orders: list, articles: dict) -> list[dict]:
    merged: dict[tuple[int, str, str], dict] = {}
    for o in orders:
        payload = json.loads(o.payload_json)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            if is_voucher_sale_line(line):
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


def _cash_register_from_event(ev: dict, cash_register_uuid: str | None) -> dict | None:
    if not cash_register_uuid:
        return None
    for reg in (ev.get("configuration") or {}).get("cash_registers") or []:
        if str(reg.get("uuid")) == str(cash_register_uuid):
            return reg
    return None


def _receipt_register_uuid(ev: dict, cash_register_uuid: str | None) -> str | None:
    if cash_register_uuid:
        return str(cash_register_uuid)
    for reg in (ev.get("configuration") or {}).get("cash_registers") or []:
        if reg.get("receipt_printer_appliance_id"):
            return str(reg.get("uuid"))
    regs = (ev.get("configuration") or {}).get("cash_registers") or []
    if regs:
        return str(regs[0].get("uuid"))
    return None


def _create_voucher_print_job(
    db: Session,
    *,
    order_id: int,
    ev: dict,
    cash_register_uuid: str | None,
    voucher_name: str,
    value_cents: int,
    copy_index: int | None = None,
    copy_total: int | None = None,
) -> int:
    reg_uuid = _receipt_register_uuid(ev, cash_register_uuid)
    host, port = _resolve_printer(ev, reg_uuid)
    esc = build_voucher_slip_text(
        event_name=ev.get("name", "Event"),
        voucher_name=voucher_name,
        value_cents=value_cents,
        currency=ev.get("currency", "EUR"),
        copy_index=copy_index,
        copy_total=copy_total,
    )
    pj = PrintJob(
        local_order_id=order_id,
        station_uuid=reg_uuid,
        printer_host=host,
        printer_port=port,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
        status="queued",
    )
    db.add(pj)
    db.flush()
    return pj.id


def _allocate_pickup_number(db: Session, event_id: int) -> int:
    counter = db.query(EventPickupCounter).filter(EventPickupCounter.event_id == event_id).first()
    if not counter:
        counter = EventPickupCounter(event_id=event_id, next_number=1)
        db.add(counter)
        db.flush()
    number = int(counter.next_number or 1)
    counter.next_number = number + 1
    db.flush()
    return number


def _payments_total_cents(payments: list[dict]) -> int:
    total = 0
    for payment in payments or []:
        if not isinstance(payment, dict):
            continue
        total += int(payment.get("amount_cents") or 0)
    return total


def _set_pickup_ready_if_complete(db: Session, order: LocalOrder) -> None:
    if order.order_source != "cash_register" or order.pickup_status in {"ready", "picked_up"}:
        return
    pending = (
        db.query(KitchenTicket)
        .filter(KitchenTicket.local_order_id == order.id, KitchenTicket.status != "done")
        .first()
    )
    if pending:
        return
    order.pickup_status = "ready"
    order.ready_at = datetime.now(timezone.utc)
    payload = json.loads(order.payload_json)
    payload["pickup_status"] = "ready"
    payload["ready_at"] = order.ready_at.isoformat()
    order.payload_json = json.dumps(payload)
    _sync_outbox_payload(db, order, payload)


def _station_config_for_uuid(ev: dict, station_uuid: str | None) -> dict | None:
    if station_uuid is None:
        return None
    for st in (ev.get("configuration") or {}).get("stations") or []:
        if str(st.get("uuid")) == str(station_uuid):
            return st
    return None


def _station_has_kitchen_monitor(ev: dict, station_uuid: str | None) -> bool:
    st = _station_config_for_uuid(ev, station_uuid)
    return bool(st and st.get("kitchen_monitor_enabled"))


def _create_print_job_for_lines(
    db: Session,
    *,
    order_id: int,
    station_uuid: str | None,
    payload: dict,
    station_lines: list[dict],
    ev: dict,
    articles: dict,
) -> int:
    station_payload = {**payload, "lines": station_lines}
    station_label = station_name_from_event(ev, station_uuid)
    host, port = _resolve_printer(ev, station_uuid)
    esc = build_escpos_receipt_text(
        station_payload,
        ev.get("name", "Event"),
        station_name=station_label,
        articles=articles,
    )
    pj = PrintJob(
        local_order_id=order_id,
        station_uuid=station_uuid,
        printer_host=host,
        printer_port=port,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
        status="queued",
    )
    db.add(pj)
    db.flush()
    return pj.id


def _create_customer_pickup_print_job_for_lines(
    db: Session,
    *,
    order_id: int,
    cash_register_uuid: str,
    station_uuid: str | None,
    payload: dict,
    station_lines: list[dict],
    ev: dict,
    articles: dict,
) -> int:
    station_payload = {**payload, "lines": station_lines}
    station_label = station_name_from_event(ev, station_uuid)
    host, port = _resolve_printer(ev, cash_register_uuid)
    esc = build_customer_pickup_text(
        station_payload,
        ev.get("name", "Event"),
        station_name=station_label,
        articles=articles,
    )
    pj = PrintJob(
        local_order_id=order_id,
        station_uuid=station_uuid,
        printer_host=host,
        printer_port=port,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
        status="queued",
    )
    db.add(pj)
    db.flush()
    return pj.id


def _create_kitchen_ticket(
    db: Session,
    *,
    order_id: int,
    event_id: int,
    station_uuid: str,
    station_lines: list[dict],
) -> int:
    ticket = KitchenTicket(
        local_order_id=order_id,
        event_id=event_id,
        station_uuid=station_uuid,
        status="open",
    )
    db.add(ticket)
    db.flush()
    for idx, line in enumerate(station_lines):
        if not isinstance(line, dict):
            continue
        qty = max(1, int(line.get("qty") or 1))
        db.add(
            KitchenTicketLine(
                ticket_id=ticket.id,
                line_index=idx,
                line_payload_json=json.dumps(dict(line)),
                qty_total=qty,
                qty_printed=0,
            )
        )
    db.flush()
    return ticket.id


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


def _cloud_gateway_http_error(e: httpx.HTTPStatusError) -> HTTPException:
    try:
        detail = e.response.json()
    except Exception:
        detail = e.response.text or "Cloud request failed"
    return HTTPException(status_code=e.response.status_code, detail=detail)


class TerminalConnectionTokenBody(BaseModel):
    event_id: int


class TerminalPaymentIntentBody(BaseModel):
    event_id: int
    amount_cents: int = Field(..., gt=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    client_order_id: str | None = Field(None, max_length=64)
    idempotency_key: str | None = Field(None, max_length=255)
    metadata: dict[str, str] = Field(default_factory=dict)


def _terminal_event_or_error(db: Session, event_id: int) -> dict:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found in local bundle")
    if "stripe_terminal" not in _event_payment_types(ev):
        raise HTTPException(status_code=403, detail="Stripe Terminal is not enabled for this event")
    return ev


@router.post("/v1/terminal/connection-token")
async def terminal_connection_token(body: TerminalConnectionTokenBody, db: Session = Depends(get_db)) -> dict:
    _terminal_event_or_error(db, body.event_id)
    try:
        return await cloud_create_terminal_connection_token(body.event_id)
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e
    except httpx.HTTPStatusError as e:
        raise _cloud_gateway_http_error(e) from e


@router.post("/v1/terminal/payment-intents")
async def terminal_payment_intent(body: TerminalPaymentIntentBody, db: Session = Depends(get_db)) -> dict:
    ev = _terminal_event_or_error(db, body.event_id)
    try:
        return await cloud_create_terminal_payment_intent(
            event_id=body.event_id,
            amount_cents=body.amount_cents,
            currency=body.currency or ev.get("currency"),
            client_order_id=body.client_order_id,
            idempotency_key=body.idempotency_key,
            metadata=body.metadata,
        )
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e
    except httpx.HTTPStatusError as e:
        raise _cloud_gateway_http_error(e) from e


@router.get("/v1/terminal/payment-intents/{payment_intent_id}")
async def terminal_payment_intent_status(
    payment_intent_id: str,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    _terminal_event_or_error(db, event_id)
    try:
        return await cloud_retrieve_terminal_payment_intent(event_id=event_id, payment_intent_id=payment_intent_id)
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e
    except httpx.HTTPStatusError as e:
        raise _cloud_gateway_http_error(e) from e


@router.get("/v1/sync/status", response_model=SyncStatusResponse)
def get_sync_status(db: Session = Depends(get_db)) -> SyncStatusResponse:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    last_sync_at = row.updated_at.isoformat() if row and row.updated_at else None
    return SyncStatusResponse.model_validate({
        **sync_status,
        "configured": is_cloud_configured(),
        "pending_outbox_count": pending_outbox_count(db),
        "bundle_last_sync_at": last_sync_at,
    })


@router.post("/v1/sync/pull", response_model=SyncPullResponse)
async def sync_pull(db: Session = Depends(get_db)) -> SyncPullResponse:
    try:
        result = await pull_bundle(db)
        reapply_pending_stock(db, result.get("bundle"))
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e
    return SyncPullResponse(ok=True, event_count=result["event_count"])


@router.get("/v1/bundle", response_model=EdgeBundleResponse)
def get_bundle(db: Session = Depends(get_db)) -> EdgeBundleResponse:
    return EdgeBundleResponse.model_validate(_get_bundle_dict(db))


@router.get("/v1/meta", response_model=SyncMetaResponse)
def get_meta(db: Session = Depends(get_db)) -> SyncMetaResponse:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row:
        return SyncMetaResponse(last_sync_at=None)
    return SyncMetaResponse(last_sync_at=row.updated_at.isoformat() if row.updated_at else None)


@router.post("/v1/sync/push", response_model=SyncPushResponse)
async def sync_push(db: Session = Depends(get_db)) -> SyncPushResponse:
    try:
        result = await push_outbox(db, retry_errors=False)
        return SyncPushResponse.model_validate(result)
    except CloudConfigError as e:
        raise _cloud_config_http_error(e) from e


def _add_waiter_name(ev: dict, payload: dict) -> None:
    if payload.get("waiter_name"):
        return
    waiter_uuid = payload.get("waiter_uuid")
    if waiter_uuid:
        name = waiter_name_from_event(ev, waiter_uuid)
        if name:
            payload["waiter_name"] = name


def _create_payment_receipt(
    db: Session,
    ev: dict,
    payload: dict,
    *,
    source_type: str,
    source_id: str | int | None = None,
) -> PaymentReceipt:
    receipt_payload = dict(payload)
    receipt_payload.setdefault("payment_status", "paid")
    receipt_payload.setdefault("paid_at", datetime.now(timezone.utc).isoformat())
    _add_waiter_name(ev, receipt_payload)
    receipt = PaymentReceipt(
        event_id=int(receipt_payload.get("event_id") or ev.get("id")),
        waiter_uuid=receipt_payload.get("waiter_uuid"),
        source_type=source_type,
        source_id=str(source_id) if source_id is not None else None,
        payload_json=json.dumps(receipt_payload),
    )
    db.add(receipt)
    db.flush()
    return receipt


def _receipt_payload_from_orders(
    ev: dict,
    orders: list[LocalOrder],
    payments: list[dict],
    *,
    table_number: int | None = None,
    collective_bill: CollectiveBill | None = None,
    paid_at: str | None = None,
) -> dict:
    lines: list[dict] = []
    order_numbers: set[int] = set()
    waiter_uuid = orders[0].waiter_uuid if orders else None
    for order in orders:
        payload = json.loads(order.payload_json)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            lines.append(dict(line))
            if line.get("order_number") is not None:
                order_numbers.add(int(line["order_number"]))
        if payload.get("order_number") is not None:
            order_numbers.add(int(payload["order_number"]))

    out: dict = {
        "event_id": int(ev.get("id")),
        "table_number": table_number,
        "waiter_uuid": waiter_uuid,
        "lines": lines,
        "payments": payments,
        "payment_status": "paid",
        "paid_at": paid_at or datetime.now(timezone.utc).isoformat(),
    }
    if table_number:
        out["settlement_table"] = table_number
    if collective_bill:
        out.update(
            {
                "table_number": None,
                "collective_bill_id": collective_bill.id,
                "collective_bill_uuid": collective_bill.uuid,
                "collective_bill_name": collective_bill.name,
                "settlement_collective_bill_id": collective_bill.id,
            }
        )
    if len(order_numbers) == 1:
        out["order_number"] = next(iter(order_numbers))
    elif order_numbers:
        out["order_numbers"] = sorted(order_numbers)
    _add_waiter_name(ev, out)
    return out


def _collective_bill_open(db: Session, bill_id: int, event_id: int) -> CollectiveBill:
    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")
    has_open = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .first()
    )
    if not has_open:
        any_order = (
            db.query(LocalOrder).filter(LocalOrder.collective_bill_id == bill.id).first()
        )
        if any_order:
            raise HTTPException(status_code=400, detail="Sammelrechnung ist bereits abgeschlossen")
    return bill


def _summary_from_orders(orders: list, ev: dict, arts: dict, extra: dict) -> dict:
    open_orders = []
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
    line_groups = _build_line_groups_from_orders(orders, arts)
    return {
        **extra,
        "currency": ev.get("currency", "EUR"),
        "open_orders": open_orders,
        "line_groups": line_groups,
        "total_cents": total_cents,
        "item_count": item_count,
    }


@router.post("/v1/orders", response_model=LocalOrderCreatedResponse)
def create_local_order(body: LocalOrderCreate, db: Session = Depends(get_db)) -> LocalOrderCreatedResponse:
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
        if isinstance(ln, dict) and ln.get("article_id") is not None and not is_voucher_sale_line(ln)
    ]
    validate_stock(ev, line_dicts)
    has_voucher_sale = any(is_voucher_sale_line(ln) for ln in body.lines if isinstance(ln, dict))

    order_source = (body.order_source or "waiter").strip().lower()
    if order_source not in {"waiter", "cash_register"}:
        raise HTTPException(status_code=400, detail="Unsupported order_source")
    if body.cash_register_uuid:
        order_source = "cash_register"

    reg = _cash_register_from_event(ev, body.cash_register_uuid)
    if order_source == "cash_register" and not reg:
        raise HTTPException(status_code=400, detail="Unknown cash register for this event")
    if order_source != "cash_register" and body.table_number is None:
        raise HTTPException(status_code=400, detail="table_number is required for waiter orders")

    pm = (ev.get("payment_mode") or "pay_later").lower()
    arts = _article_map(ev)
    payments = list(body.payments or [])
    line_cents, _ = _line_totals(body.lines, arts, ev)
    redemptions_in = [r.model_dump() for r in body.voucher_redemptions]
    if redemptions_in and not payments:
        raise HTTPException(status_code=400, detail="Gutschein einlösen erfordert Zahlung")
    article_gross, _ = order_lines_total_cents(article_lines_only(body.lines), ev, arts)
    voucher_credit = 0
    voucher_records: list[dict] = []
    if redemptions_in:
        voucher_credit, voucher_records = compute_voucher_credits(
            ev,
            gross_cents=article_gross,
            redemptions=redemptions_in,
            articles=arts,
        )
    expected_cents = max(0, line_cents - voucher_credit)
    if has_voucher_sale and order_source != "cash_register" and pm not in ("instant",) and not payments:
        raise HTTPException(status_code=400, detail="Gutscheinverkauf erfordert Zahlung")
    if order_source == "cash_register":
        if not payments:
            raise HTTPException(status_code=400, detail="payments required for cash-register orders")
        if _payments_total_cents(payments) != expected_cents:
            raise HTTPException(status_code=400, detail="payment amount must match order total")
    elif pm == "instant":
        payments = [{"type": "instant", "amount_cents": line_cents}]

    if payments:
        _validate_payment_types(ev, payments)

    payment_status = "paid" if order_source == "cash_register" else _payment_status_for_create(ev, payments)
    if has_voucher_sale and payment_status != "paid":
        raise HTTPException(status_code=400, detail="Gutscheinverkauf erfordert Zahlung")
    order_lines = _lines_with_station_uuid(ev, body.lines)
    article_order_lines = article_lines_only(order_lines)
    table_number_payload = None if order_source == "cash_register" else body.table_number
    table_number_db = 0 if order_source == "cash_register" else body.table_number
    pickup_number: int | None = None
    pickup_code: str | None = None
    pickup_status: str | None = None
    if order_source == "cash_register":
        pickup_number = _allocate_pickup_number(db, body.event_id)
        prefix = str(reg.get("pickup_code_prefix") or "").strip().upper()
        pickup_code = f"{prefix}{pickup_number}"
        pickup_status = "pending"
    payload: dict = {
        "client_order_id": body.client_order_id,
        "event_id": body.event_id,
        "table_number": table_number_payload,
        "waiter_uuid": body.waiter_uuid,
        "lines": order_lines,
        "payments": payments,
        "payment_status": payment_status,
        "order_source": order_source,
    }
    if voucher_records:
        payload["voucher_redemptions"] = voucher_records
        payload["voucher_credit_cents"] = voucher_credit
    if order_source == "cash_register":
        payload.update(
            {
                "cash_register_uuid": body.cash_register_uuid,
                "cash_register_name": reg.get("name"),
                "pickup_prefix": reg.get("pickup_code_prefix"),
                "pickup_number": pickup_number,
                "pickup_code": pickup_code,
                "pickup_status": pickup_status,
            }
        )
    order_number: int | None = None
    if is_ferdig_client_order_id(body.client_order_id):
        order_number = allocate_order_number(db, body.event_id)
        ordered_at = datetime.now(timezone.utc).isoformat()
        waiter_name = waiter_name_from_event(ev, body.waiter_uuid)
        order_lines = snapshot_lines(order_lines, arts, order_number=order_number)
        payload["order_number"] = order_number
        payload["ordered_at"] = ordered_at
        payload["lines"] = order_lines
        if waiter_name:
            payload["waiter_name"] = waiter_name
    order = LocalOrder(
        client_order_id=body.client_order_id,
        event_id=body.event_id,
        table_number=table_number_db,
        waiter_uuid=body.waiter_uuid,
        order_source=order_source,
        cash_register_uuid=body.cash_register_uuid if order_source == "cash_register" else None,
        pickup_code=pickup_code,
        pickup_status=pickup_status,
        payment_status=payment_status,
        payload_json=json.dumps(payload),
        print_status="pending",
    )
    db.add(order)
    db.flush()

    groups = group_lines_by_station(ev, article_order_lines)
    print_job_ids: list[int] = []
    customer_print_job_ids: list[int] = []
    kitchen_ticket_ids: list[int] = []

    if payment_status == "paid" and has_voucher_sale:
        slip_units: list[tuple[str, int]] = []
        for line in order_lines:
            if not is_voucher_sale_line(line):
                continue
            vd = voucher_definition_by_uuid(ev, str(line.get("voucher_definition_uuid") or ""))
            name = (vd or {}).get("name") or "Gutschein"
            uc = voucher_sale_unit_cents(ev, line)
            qty = max(1, int(line.get("qty") or 1))
            slip_units.extend([(name, uc)] * qty)
        total_slips = len(slip_units)
        for idx, (vname, uc) in enumerate(slip_units, start=1):
            print_job_ids.append(
                _create_voucher_print_job(
                    db,
                    order_id=order.id,
                    ev=ev,
                    cash_register_uuid=body.cash_register_uuid,
                    voucher_name=vname,
                    value_cents=uc,
                    copy_index=idx if total_slips > 1 else None,
                    copy_total=total_slips if total_slips > 1 else None,
                )
            )

    for station_uuid, station_lines in groups.items():
        if _station_has_kitchen_monitor(ev, station_uuid) and station_uuid is not None:
            kitchen_ticket_ids.append(
                _create_kitchen_ticket(
                    db,
                    order_id=order.id,
                    event_id=body.event_id,
                    station_uuid=str(station_uuid),
                    station_lines=station_lines,
                )
            )
        else:
            print_job_ids.append(
                _create_print_job_for_lines(
                    db,
                    order_id=order.id,
                    station_uuid=station_uuid,
                    payload=payload,
                    station_lines=station_lines,
                    ev=ev,
                    articles=arts,
                )
            )
        if order_source == "cash_register":
            customer_print_job_ids.append(
                _create_customer_pickup_print_job_for_lines(
                    db,
                    order_id=order.id,
                    cash_register_uuid=str(body.cash_register_uuid),
                    station_uuid=station_uuid,
                    payload=payload,
                    station_lines=station_lines,
                    ev=ev,
                    articles=arts,
                )
            )

    if order_source == "cash_register" and not kitchen_ticket_ids:
        _set_pickup_ready_if_complete(db, order)
        payload = json.loads(order.payload_json)

    out = OutboxEntry(
        client_order_id=body.client_order_id,
        event_id=body.event_id,
        payload_json=json.dumps(payload),
        status="pending",
    )
    db.add(out)

    articles_patch = apply_stock_to_bundle(bundle, body.event_id, line_dicts)
    save_bundle(db, bundle)

    payment_receipt_id = None
    if order_source != "cash_register" and payment_status == "paid" and payments:
        payment_receipt_id = _create_payment_receipt(
            db,
            ev,
            payload,
            source_type="order",
            source_id=order.id,
        ).id

    db.commit()
    return LocalOrderCreatedResponse(
        local_order_id=order.id,
        payment_id=payment_receipt_id,
        order_number=order_number,
        print_job_id=print_job_ids[0] if print_job_ids else None,
        print_job_ids=print_job_ids,
        customer_print_job_ids=customer_print_job_ids,
        kitchen_ticket_ids=kitchen_ticket_ids,
        payment_status=payment_status,
        pickup_code=pickup_code,
        pickup_status=payload.get("pickup_status") if order_source == "cash_register" else None,
        payment_mode=(ev.get("payment_mode") or "pay_later").lower(),
        articles=articles_patch,
    )


@router.post("/v1/orders/{order_id}/pay", response_model=OrderPayResponse)
def pay_local_order(order_id: int, body: OrderPayBody, db: Session = Depends(get_db)) -> OrderPayResponse:
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
    payload["paid_at"] = datetime.now(timezone.utc).isoformat()
    order.payment_status = "paid"
    order.payload_json = json.dumps(payload)
    _sync_outbox_payload(db, order, payload)
    receipt = _create_payment_receipt(db, ev, payload, source_type="order", source_id=order.id)
    db.commit()
    return OrderPayResponse(local_order_id=order.id, payment_id=receipt.id, payment_status="paid")


@router.get("/v1/tables/open", response_model=OpenTablesResponse)
def list_open_tables(event_id: int = Query(...), db: Session = Depends(get_db)) -> OpenTablesResponse:
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
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.table_number > 0,
        )
        .order_by(LocalOrder.table_number.asc(), LocalOrder.id.asc())
        .all()
    )

    by_table: dict[int, dict] = {}
    table_order_sets: dict[int, set] = {}
    for o in orders:
        tn = int(o.table_number)
        if tn not in by_table:
            by_table[tn] = {"table_number": tn, "order_count": 0, "total_cents": 0, "item_count": 0}
            table_order_sets[tn] = set()
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        line_cents, line_qty = _line_totals(lines, arts)
        table_order_sets[tn] |= distinct_order_numbers_from_payload(payload, legacy_key=f"legacy:{o.id}")
        by_table[tn]["total_cents"] += line_cents
        by_table[tn]["item_count"] += line_qty

    for tn, row in by_table.items():
        row["order_count"] = len(table_order_sets.get(tn, set()))

    tables = [
        {**row, "currency": currency}
        for row in sorted(by_table.values(), key=lambda r: r["table_number"])
    ]
    return OpenTablesResponse(event_id=event_id, currency=currency, tables=tables)


@router.get("/v1/tables/{table_number}", response_model=AccountSummaryResponse)
def get_table_summary(
    table_number: int,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> AccountSummaryResponse:
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
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )

    summary = _summary_from_orders(
        orders,
        ev,
        arts,
        {"table_number": table_number, "event_id": event_id},
    )
    aggregated_lines = []
    for o in orders:
        payload = json.loads(o.payload_json)
        for line in payload.get("lines") or []:
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
    summary["aggregated_lines"] = aggregated_lines
    return AccountSummaryResponse.model_validate(summary)


@router.post("/v1/tables/{table_number}/settle-partial", response_model=TablePartialSettleResponse)
def settle_table_partial(
    table_number: int, body: TableSettlePartialBody, db: Session = Depends(get_db)
) -> TablePartialSettleResponse:
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

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    line_groups = _build_line_groups_from_orders(orders, arts)
    gross_cents = _selections_total_cents_from_groups(selections, line_groups)
    redemptions_in = [r.model_dump() for r in body.voucher_redemptions]
    voucher_credit, voucher_records = compute_voucher_credits(
        ev,
        gross_cents=gross_cents,
        redemptions=redemptions_in,
        articles=arts,
        selections=selections,
        line_groups=line_groups,
    )
    expected_cents = max(0, gross_cents - voucher_credit)
    paid_total = sum(int(p.get("amount_cents") or 0) for p in body.payments if isinstance(p, dict))
    if paid_total != expected_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match payable {expected_cents}",
        )

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
            if is_voucher_sale_line(line):
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
                copy_line_fiscal_fields(line, pl)
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
    payment_id = None
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
            "voucher_redemptions": voucher_records,
            "voucher_credit_cents": voucher_credit,
        }
        order_nums = {int(ln["order_number"]) for ln in paid_lines if ln.get("order_number") is not None}
        if len(order_nums) == 1:
            paid_payload["order_number"] = order_nums.pop()
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
        payment_id = _create_payment_receipt(
            db,
            ev,
            paid_payload,
            source_type="table_partial",
            source_id=paid_order.id,
        ).id
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
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    remaining_cents = 0
    for o in remaining_orders:
        payload = json.loads(o.payload_json)
        cents, _ = _line_totals(payload.get("lines") or [], arts)
        remaining_cents += cents

    return TablePartialSettleResponse(
        paid_cents=expected_cents,
        remaining_cents=remaining_cents,
        paid_order_ids=paid_order_ids,
        payment_id=payment_id,
        table_number=table_number,
        voucher_credit_cents=voucher_credit,
    )


@router.post("/v1/tables/{table_number}/settle", response_model=TableSettleResponse)
def settle_table(
    table_number: int, body: TableSettleBody, db: Session = Depends(get_db)
) -> TableSettleResponse:
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
            LocalOrder.collective_bill_id.is_(None),
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

    receipt_payload = _receipt_payload_from_orders(
        ev,
        orders,
        body.payments,
        table_number=table_number,
        paid_at=now,
    )
    receipt = _create_payment_receipt(
        db,
        ev,
        receipt_payload,
        source_type="table",
        source_id=table_number,
    )
    db.commit()
    return TableSettleResponse(
        paid_order_ids=paid_ids,
        payment_id=receipt.id,
        total_cents=total_cents,
        table_number=table_number,
    )


def _selections_from_body(selections: list[LineSelection]) -> list[dict]:
    return [s.model_dump() for s in selections]


@router.post("/v1/tables/{from_table}/transfer-lines", response_model=TransferLinesResponse)
def transfer_table_lines(
    from_table: int, body: TransferLinesBody, db: Session = Depends(get_db)
) -> TransferLinesResponse:
    if from_table < 1 or from_table > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")
    if body.target_table_number == from_table:
        raise HTTPException(status_code=400, detail="Ziel-Tisch muss ein anderer Tisch sein")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")

    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == from_table,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    selections = _selections_from_body(body.selections)
    try:
        moved = take_from_orders(db, orders, selections, _sync_outbox_payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    waiter_uuid = orders[0].waiter_uuid if orders else None
    append_lines_to_table(
        db,
        ev=ev,
        event_id=body.event_id,
        target_table=body.target_table_number,
        waiter_uuid=waiter_uuid,
        lines=moved,
        lines_with_station=_lines_with_station_uuid,
        sync_outbox=_sync_outbox_payload,
    )
    db.commit()
    return TransferLinesResponse(
        from_table=from_table,
        target_table_number=body.target_table_number,
        moved_line_count=len(moved),
    )


@router.post("/v1/tables/{from_table}/assign-collective", response_model=AssignCollectiveResponse)
def assign_table_to_collective(
    from_table: int, body: AssignCollectiveBody, db: Session = Depends(get_db)
) -> AssignCollectiveResponse:
    if from_table < 1 or from_table > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")
    if body.collective_bill_id is None and not body.new_name:
        raise HTTPException(status_code=400, detail="collective_bill_id or new_name required")

    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    if body.new_name:
        bill = CollectiveBill(
            uuid=str(uuid.uuid4()),
            event_id=body.event_id,
            name=body.new_name.strip(),
        )
        db.add(bill)
        db.flush()
    else:
        bill = _collective_bill_open(db, body.collective_bill_id, body.event_id)

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == from_table,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    selections = _selections_from_body(body.selections)
    try:
        moved = take_from_orders(db, orders, selections, _sync_outbox_payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    waiter_uuid = orders[0].waiter_uuid if orders else None
    append_lines_to_collective(
        db,
        ev=ev,
        bill=bill,
        event_id=body.event_id,
        waiter_uuid=waiter_uuid,
        lines=moved,
        lines_with_station=_lines_with_station_uuid,
        sync_outbox=_sync_outbox_payload,
    )
    db.commit()
    return AssignCollectiveResponse(
        collective_bill_id=bill.id,
        collective_bill_uuid=bill.uuid,
        name=bill.name,
        from_table=from_table,
    )


@router.post("/v1/collective-bills", response_model=CollectiveBillCreatedResponse)
def create_collective_bill(
    body: CollectiveBillCreateBody, db: Session = Depends(get_db)
) -> CollectiveBillCreatedResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = CollectiveBill(
        uuid=str(uuid.uuid4()),
        event_id=body.event_id,
        name=body.name.strip(),
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return CollectiveBillCreatedResponse(
        id=bill.id,
        uuid=bill.uuid,
        name=bill.name,
        event_id=bill.event_id,
        total_cents=0,
        order_count=0,
    )


@router.get("/v1/collective-bills/open", response_model=OpenCollectiveBillsResponse)
def list_open_collective_bills(
    event_id: int = Query(...), db: Session = Depends(get_db)
) -> OpenCollectiveBillsResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    arts = _article_map(ev)
    currency = ev.get("currency", "EUR")
    bills = db.query(CollectiveBill).filter(CollectiveBill.event_id == event_id).order_by(CollectiveBill.id.asc()).all()
    result = []
    for bill in bills:
        open_orders = (
            db.query(LocalOrder)
            .filter(
                LocalOrder.collective_bill_id == bill.id,
                LocalOrder.payment_status == "open",
            )
            .all()
        )
        has_any_order = (
            db.query(LocalOrder.id)
            .filter(LocalOrder.collective_bill_id == bill.id)
            .first()
            is not None
        )
        if has_any_order and not open_orders:
            continue
        total_cents = 0
        order_count = distinct_order_numbers_for_local_orders(open_orders)
        item_count = 0
        for o in open_orders:
            payload = json.loads(o.payload_json)
            cents, qty = _line_totals(payload.get("lines") or [], arts)
            total_cents += cents
            item_count += qty
        result.append(
            {
                "id": bill.id,
                "uuid": bill.uuid,
                "name": bill.name,
                "order_count": order_count,
                "total_cents": total_cents,
                "item_count": item_count,
                "currency": currency,
            }
        )
    return OpenCollectiveBillsResponse(
        event_id=event_id, currency=currency, collective_bills=result
    )


@router.get("/v1/collective-bills/{bill_id}", response_model=AccountSummaryResponse)
def get_collective_bill_summary(
    bill_id: int,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> AccountSummaryResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")

    arts = _article_map(ev)
    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    summary = _summary_from_orders(
        orders,
        ev,
        arts,
        {
            "collective_bill_id": bill.id,
            "collective_bill_uuid": bill.uuid,
            "name": bill.name,
            "event_id": event_id,
        },
    )
    return AccountSummaryResponse.model_validate(summary)


def _settle_orders_partial(
    db: Session,
    ev: dict,
    body: TableSettlePartialBody,
    orders: list,
    *,
    settlement_meta: dict,
    paid_order_prefix: str,
) -> dict:
    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")

    _validate_payment_types(ev, body.payments)

    arts = _article_map(ev)
    selections = [s.model_dump() for s in body.selections]

    if not orders:
        raise HTTPException(status_code=404, detail="No open orders")

    line_groups = _build_line_groups_from_orders(orders, arts)
    gross_cents = _selections_total_cents_from_groups(selections, line_groups)
    redemptions_in = [r.model_dump() for r in body.voucher_redemptions]
    voucher_credit, voucher_records = compute_voucher_credits(
        ev,
        gross_cents=gross_cents,
        redemptions=redemptions_in,
        articles=arts,
        selections=selections,
        line_groups=line_groups,
    )
    expected_cents = max(0, gross_cents - voucher_credit)
    paid_total = sum(int(p.get("amount_cents") or 0) for p in body.payments if isinstance(p, dict))
    if paid_total != expected_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match payable {expected_cents}",
        )

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
            if is_voucher_sale_line(line):
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
                copy_line_fiscal_fields(line, pl)
                paid_lines.append(pl)
                need[key] = need.get(key, 0) - take
                qty -= take
            if qty > 0:
                open_lines.append({**line, "qty": qty, "additions": adds})
        payload["lines"] = open_lines
        if open_lines:
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)
        else:
            order.payment_status = "paid"
            payload["payment_status"] = "paid"
            payload["settled_at"] = now
            payload.update(settlement_meta)
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)

    leftover = sum(v for v in need.values() if v > 0)
    if leftover > 0:
        raise HTTPException(status_code=400, detail="Selection exceeds open quantities")

    paid_order_ids: list[int] = []
    payment_id = None
    if paid_lines:
        pay_cid = f"{paid_order_prefix}-{uuid.uuid4().hex[:12]}"
        paid_lines = _lines_with_station_uuid(ev, paid_lines)
        paid_payload = {
            "client_order_id": pay_cid,
            "event_id": body.event_id,
            "waiter_uuid": orders[0].waiter_uuid if orders else None,
            "lines": paid_lines,
            "payments": body.payments,
            "payment_status": "paid",
            "settled_at": now,
            "partial_settlement": True,
            "voucher_redemptions": voucher_records,
            "voucher_credit_cents": voucher_credit,
            **settlement_meta,
        }
        order_nums = {int(ln["order_number"]) for ln in paid_lines if ln.get("order_number") is not None}
        if len(order_nums) == 1:
            paid_payload["order_number"] = order_nums.pop()
        coll_id = settlement_meta.get("collective_bill_id")
        paid_order = LocalOrder(
            client_order_id=pay_cid,
            event_id=body.event_id,
            table_number=0 if coll_id else settlement_meta.get("table_number"),
            collective_bill_id=coll_id,
            waiter_uuid=orders[0].waiter_uuid if orders else None,
            payment_status="paid",
            payload_json=json.dumps(paid_payload),
            print_status="done",
        )
        db.add(paid_order)
        db.flush()
        paid_order_ids.append(paid_order.id)
        payment_id = _create_payment_receipt(
            db,
            ev,
            paid_payload,
            source_type="collective_partial" if settlement_meta.get("collective_bill_id") else "table_partial",
            source_id=paid_order.id,
        ).id
        db.add(
            OutboxEntry(
                client_order_id=pay_cid,
                event_id=body.event_id,
                payload_json=json.dumps(paid_payload),
                status="pending",
            )
        )

    return {
        "paid_cents": expected_cents,
        "paid_order_ids": paid_order_ids,
        "payment_id": payment_id,
    }


@router.post("/v1/collective-bills/{bill_id}/settle-partial", response_model=CollectivePartialSettleResponse)
def settle_collective_partial(
    bill_id: int,
    body: TableSettlePartialBody,
    db: Session = Depends(get_db),
) -> CollectivePartialSettleResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == body.event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )

    meta = {
        "table_number": None,
        "collective_bill_id": bill.id,
        "collective_bill_uuid": bill.uuid,
        "collective_bill_name": bill.name,
        "settlement_collective_bill_id": bill.id,
    }
    result = _settle_orders_partial(
        db,
        ev,
        body,
        orders,
        settlement_meta=meta,
        paid_order_prefix=f"partial-coll-{bill.id}",
    )
    db.commit()

    remaining_orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    arts = _article_map(ev)
    remaining_cents = 0
    for o in remaining_orders:
        payload = json.loads(o.payload_json)
        cents, _ = _line_totals(payload.get("lines") or [], arts)
        remaining_cents += cents

    return CollectivePartialSettleResponse(
        paid_cents=result["paid_cents"],
        paid_order_ids=result["paid_order_ids"],
        payment_id=result["payment_id"],
        remaining_cents=remaining_cents,
        collective_bill_id=bill.id,
    )


@router.post("/v1/collective-bills/{bill_id}/settle", response_model=CollectiveSettleResponse)
def settle_collective(
    bill_id: int, body: TableSettleBody, db: Session = Depends(get_db)
) -> CollectiveSettleResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == body.event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this Sammelrechnung")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")

    _validate_payment_types(ev, body.payments)

    now = datetime.now(timezone.utc).isoformat()
    arts = _article_map(ev)
    total_cents = 0
    for o in orders:
        payload = json.loads(o.payload_json)
        cents, _ = _line_totals(payload.get("lines") or [], arts)
        total_cents += cents

    paid_total = sum(int(p.get("amount_cents") or 0) for p in body.payments if isinstance(p, dict))
    if paid_total != total_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match open balance {total_cents}",
        )

    meta = {
        "table_number": None,
        "collective_bill_uuid": bill.uuid,
        "collective_bill_name": bill.name,
        "settlement_collective_bill_id": bill.id,
    }
    paid_ids = []
    for o in orders:
        payload = json.loads(o.payload_json)
        payload["payments"] = body.payments
        payload["payment_status"] = "paid"
        payload["settled_at"] = now
        payload.update(meta)
        o.payment_status = "paid"
        o.payload_json = json.dumps(payload)
        _sync_outbox_payload(db, o, payload)
        paid_ids.append(o.id)

    receipt_payload = _receipt_payload_from_orders(
        ev,
        orders,
        body.payments,
        collective_bill=bill,
        paid_at=now,
    )
    receipt = _create_payment_receipt(
        db,
        ev,
        receipt_payload,
        source_type="collective",
        source_id=bill.id,
    )
    db.commit()
    return CollectiveSettleResponse(
        paid_order_ids=paid_ids,
        payment_id=receipt.id,
        total_cents=total_cents,
        collective_bill_id=bill.id,
    )


def _bundle_dict_optional(db: Session) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    if not isinstance(data, dict) or data.get("organisation_id") is None:
        return None
    return data


@router.get("/v1/admin/status", response_model=AdminStatusResponse)
def admin_status(db: Session = Depends(get_db)) -> AdminStatusResponse:
    bundle = _bundle_dict_optional(db)
    bundle_ready = bundle is not None
    hashes = (bundle or {}).get("admin_pin_hashes") or []
    return AdminStatusResponse(
        bundle_ready=bundle_ready,
        requires_pin=bundle_ready and len(hashes) > 0,
    )


@router.post("/v1/admin/verify", response_model=OkResponse)
def verify_admin_pin(body: AdminVerifyBody, db: Session = Depends(get_db)) -> OkResponse:
    if not body.pin.isdigit():
        raise HTTPException(status_code=401, detail="Invalid admin code")
    bundle = _bundle_dict_optional(db)
    if bundle is None:
        raise HTTPException(status_code=401, detail="Invalid admin code")
    hashes = bundle.get("admin_pin_hashes") or []
    if not hashes:
        raise HTTPException(status_code=401, detail="no_admin_pins_configured")
    for h in hashes:
        if not h or not isinstance(h, str):
            continue
        try:
            if verify_password(body.pin, h):
                return OkResponse()
        except Exception:
            continue
    raise HTTPException(status_code=401, detail="Invalid admin code")


def _kitchen_stations_for_event(ev: dict) -> list[dict]:
    stations = []
    for st in (ev.get("configuration") or {}).get("stations") or []:
        if not st.get("kitchen_monitor_enabled"):
            continue
        if not st.get("uuid"):
            continue
        stations.append(
            {
                "uuid": str(st["uuid"]),
                "name": st.get("name") or f"Station {str(st['uuid'])[:8]}",
                "sort_order": int(st.get("sort_order") or 0),
            }
        )
    return sorted(stations, key=lambda s: (s["sort_order"], s["name"]))


def _kitchen_line_response(row: KitchenTicketLine, articles: dict) -> dict:
    line = json.loads(row.line_payload_json)
    aid = line.get("article_id")
    art = articles.get(str(aid)) or articles.get(aid) or {}
    if aid is not None and not line.get("article_name"):
        line["article_name"] = art.get("name") or f"#{aid}"
    remaining = max(0, int(row.qty_total or 0) - int(row.qty_printed or 0))
    return {
        "id": row.id,
        "line_index": row.line_index,
        "line": line,
        "qty_total": int(row.qty_total or 0),
        "qty_printed": int(row.qty_printed or 0),
        "qty_remaining": remaining,
    }


def _serialize_kitchen_ticket(
    ticket: KitchenTicket,
    order: LocalOrder,
    lines: list[KitchenTicketLine],
    ev: dict,
) -> dict:
    payload = json.loads(order.payload_json)
    arts = _article_map(ev)
    line_rows = [_kitchen_line_response(row, arts) for row in sorted(lines, key=lambda r: (r.line_index, r.id))]
    line_rows = [row for row in line_rows if row["qty_remaining"] > 0]
    return {
        "id": ticket.id,
        "local_order_id": ticket.local_order_id,
        "event_id": ticket.event_id,
        "station_uuid": ticket.station_uuid,
        "station_name": station_name_from_event(ev, ticket.station_uuid),
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "client_order_id": order.client_order_id,
        "table_number": payload.get("table_number"),
        "pickup_code": payload.get("pickup_code"),
        "order_source": payload.get("order_source") or "waiter",
        "waiter_uuid": payload.get("waiter_uuid"),
        "waiter_name": payload.get("waiter_name"),
        "order_number": payload.get("order_number"),
        "ordered_at": payload.get("ordered_at"),
        "lines": line_rows,
    }


def _update_kitchen_ticket_status(db: Session, ticket: KitchenTicket) -> None:
    lines = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).all()
    remaining = sum(max(0, int(ln.qty_total or 0) - int(ln.qty_printed or 0)) for ln in lines)
    printed = sum(int(ln.qty_printed or 0) for ln in lines)
    if remaining <= 0:
        ticket.status = "done"
    elif printed > 0:
        ticket.status = "partial"
    else:
        ticket.status = "open"


def _enqueue_kitchen_ticket_print(
    db: Session,
    *,
    ticket: KitchenTicket,
    selected_lines: list[tuple[KitchenTicketLine, int]],
) -> int:
    order = db.query(LocalOrder).filter(LocalOrder.id == ticket.local_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, ticket.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    if not _station_has_kitchen_monitor(ev, ticket.station_uuid):
        raise HTTPException(status_code=400, detail="Kitchen monitor is not active for this station")

    payload = json.loads(order.payload_json)
    printable_lines: list[dict] = []
    for line_row, qty in selected_lines:
        remaining = max(0, int(line_row.qty_total or 0) - int(line_row.qty_printed or 0))
        qty = int(qty)
        if qty < 1 or qty > remaining:
            raise HTTPException(status_code=400, detail="Requested quantity exceeds remaining quantity")
        line = json.loads(line_row.line_payload_json)
        line["qty"] = qty
        printable_lines.append(line)

    if not printable_lines:
        raise HTTPException(status_code=400, detail="Nothing left to print")

    job_id = _create_print_job_for_lines(
        db,
        order_id=order.id,
        station_uuid=ticket.station_uuid,
        payload=payload,
        station_lines=printable_lines,
        ev=ev,
        articles=_article_map(ev),
    )
    for line_row, qty in selected_lines:
        line_row.qty_printed = int(line_row.qty_printed or 0) + int(qty)
    _update_kitchen_ticket_status(db, ticket)
    db.flush()
    _set_pickup_ready_if_complete(db, order)
    db.commit()
    return job_id


@router.get("/v1/kitchen/stations", response_model=KitchenStationsResponse)
def list_kitchen_stations(event_id: int = Query(...), db: Session = Depends(get_db)) -> KitchenStationsResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    return KitchenStationsResponse(stations=_kitchen_stations_for_event(ev))


@router.get("/v1/kitchen/orders", response_model=KitchenOrdersResponse)
def list_kitchen_orders(
    event_id: int = Query(...),
    station_uuid: str = Query(...),
    db: Session = Depends(get_db),
) -> KitchenOrdersResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    if not _station_has_kitchen_monitor(ev, station_uuid):
        raise HTTPException(status_code=400, detail="Kitchen monitor is not active for this station")

    tickets = (
        db.query(KitchenTicket)
        .filter(
            KitchenTicket.event_id == event_id,
            KitchenTicket.station_uuid == station_uuid,
            KitchenTicket.status != "done",
        )
        .order_by(KitchenTicket.id.asc())
        .all()
    )
    out = []
    for ticket in tickets:
        order = db.query(LocalOrder).filter(LocalOrder.id == ticket.local_order_id).first()
        if not order:
            continue
        lines = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).all()
        serialized = _serialize_kitchen_ticket(ticket, order, lines, ev)
        if serialized["lines"]:
            out.append(serialized)
    return KitchenOrdersResponse(orders=out)


@router.post("/v1/kitchen/tickets/{ticket_id}/print", response_model=KitchenTicketPrintResponse)
def print_kitchen_ticket(ticket_id: int, db: Session = Depends(get_db)) -> KitchenTicketPrintResponse:
    ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found")
    if ticket.status == "done":
        raise HTTPException(status_code=400, detail="Kitchen ticket is already done")
    lines = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).all()
    selected = [
        (ln, max(0, int(ln.qty_total or 0) - int(ln.qty_printed or 0)))
        for ln in lines
        if max(0, int(ln.qty_total or 0) - int(ln.qty_printed or 0)) > 0
    ]
    job_id = _enqueue_kitchen_ticket_print(db, ticket=ticket, selected_lines=selected)
    return KitchenTicketPrintResponse(print_job_id=job_id, ticket_status=ticket.status)


@router.post("/v1/kitchen/tickets/{ticket_id}/lines/{line_id}/print-one", response_model=KitchenTicketPrintResponse)
def print_kitchen_ticket_line_unit(ticket_id: int, line_id: int, db: Session = Depends(get_db)) -> KitchenTicketPrintResponse:
    ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found")
    if ticket.status == "done":
        raise HTTPException(status_code=400, detail="Kitchen ticket is already done")
    line = (
        db.query(KitchenTicketLine)
        .filter(KitchenTicketLine.id == line_id, KitchenTicketLine.ticket_id == ticket.id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Kitchen ticket line not found")
    job_id = _enqueue_kitchen_ticket_print(db, ticket=ticket, selected_lines=[(line, 1)])
    return KitchenTicketPrintResponse(print_job_id=job_id, ticket_status=ticket.status)


def _pickup_order_response(order: LocalOrder) -> dict[str, Any]:
    payload = json.loads(order.payload_json)
    return {
        "local_order_id": order.id,
        "client_order_id": order.client_order_id,
        "pickup_code": order.pickup_code or payload.get("pickup_code"),
        "pickup_status": order.pickup_status or payload.get("pickup_status") or "pending",
        "cash_register_uuid": order.cash_register_uuid or payload.get("cash_register_uuid"),
        "cash_register_name": payload.get("cash_register_name"),
        "order_number": payload.get("order_number"),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "ready_at": order.ready_at.isoformat() if order.ready_at else payload.get("ready_at"),
        "item_count": sum(max(1, int(line.get("qty") or 1)) for line in payload.get("lines") or [] if isinstance(line, dict)),
    }


READY_PICKUP_TTL = timedelta(minutes=5)


def _mark_pickup_order_picked_up(db: Session, order: LocalOrder) -> None:
    order.pickup_status = "picked_up"
    order.picked_up_at = datetime.now(timezone.utc)
    payload = json.loads(order.payload_json)
    payload["pickup_status"] = "picked_up"
    payload["picked_up_at"] = order.picked_up_at.isoformat()
    order.payload_json = json.dumps(payload)
    _sync_outbox_payload(db, order, payload)


def _expire_stale_ready_pickup_orders(db: Session, event_id: int) -> None:
    cutoff = datetime.now(timezone.utc) - READY_PICKUP_TTL
    stale = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.order_source == "cash_register",
            LocalOrder.pickup_status == "ready",
            LocalOrder.ready_at.isnot(None),
            LocalOrder.ready_at < cutoff,
        )
        .all()
    )
    for order in stale:
        _mark_pickup_order_picked_up(db, order)


@router.get("/v1/pickup/orders", response_model=PickupOrdersResponse)
def list_pickup_orders(event_id: int = Query(...), db: Session = Depends(get_db)) -> PickupOrdersResponse:
    _expire_stale_ready_pickup_orders(db, event_id)
    db.commit()
    rows = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.order_source == "cash_register",
            LocalOrder.pickup_status.in_(["pending", "ready"]),
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    pending = [row for row in rows if row.pickup_status != "ready"]
    ready = sorted(
        (row for row in rows if row.pickup_status == "ready"),
        key=lambda row: row.ready_at or datetime.min.replace(tzinfo=timezone.utc),
    )
    return PickupOrdersResponse(orders=[_pickup_order_response(row) for row in pending + ready])


@router.post("/v1/pickup/orders/{order_id}/picked-up", response_model=PickupPickedUpResponse)
def mark_pickup_order_picked_up(order_id: int, db: Session = Depends(get_db)) -> PickupPickedUpResponse:
    order = db.query(LocalOrder).filter(LocalOrder.id == order_id).first()
    if not order or order.order_source != "cash_register":
        raise HTTPException(status_code=404, detail="Pickup order not found")
    _mark_pickup_order_picked_up(db, order)
    db.commit()
    return PickupPickedUpResponse(local_order_id=order.id, pickup_status="picked_up")


@router.get("/v1/registers/{cash_register_uuid}/display", response_model=RegisterDisplayResponse)
def get_register_display(
    cash_register_uuid: str, event_id: int = Query(...), db: Session = Depends(get_db)
) -> RegisterDisplayResponse:
    row = db.query(RegisterDisplayState).filter(RegisterDisplayState.cash_register_uuid == cash_register_uuid).first()
    if not row or int(row.event_id) != int(event_id):
        return RegisterDisplayResponse(
            cash_register_uuid=cash_register_uuid,
            event_id=event_id,
            payload={},
            updated_at=None,
        )
    return RegisterDisplayResponse(
        cash_register_uuid=cash_register_uuid,
        event_id=row.event_id,
        payload=json.loads(row.payload_json or "{}"),
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.put("/v1/registers/{cash_register_uuid}/display", response_model=RegisterDisplayResponse)
def put_register_display(
    cash_register_uuid: str, body: RegisterDisplayBody, db: Session = Depends(get_db)
) -> RegisterDisplayResponse:
    row = db.query(RegisterDisplayState).filter(RegisterDisplayState.cash_register_uuid == cash_register_uuid).first()
    if not row:
        row = RegisterDisplayState(cash_register_uuid=cash_register_uuid, event_id=body.event_id)
        db.add(row)
    row.event_id = body.event_id
    row.payload_json = json.dumps(body.payload or {})
    db.commit()
    db.refresh(row)
    return RegisterDisplayResponse(
        cash_register_uuid=cash_register_uuid,
        event_id=row.event_id,
        payload=json.loads(row.payload_json or "{}"),
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.get("/v1/payments", response_model=PaymentsListResponse)
def list_payments(
    event_id: int = Query(...),
    waiter_uuid: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaymentsListResponse:
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    arts = _article_map(ev)
    q = db.query(PaymentReceipt).filter(PaymentReceipt.event_id == event_id)
    if waiter_uuid:
        q = q.filter(PaymentReceipt.waiter_uuid == waiter_uuid)
    rows = q.order_by(PaymentReceipt.id.desc()).limit(limit).all()
    payments = []
    for row in rows:
        payload = json.loads(row.payload_json or "{}")
        line_total, item_count = _line_totals(payload.get("lines") or [], arts)
        paid_total = _payments_total_cents(payload.get("payments") or []) or line_total
        payments.append(
            {
                "payment_id": row.id,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "paid_at": payload.get("paid_at") or payload.get("settled_at"),
                "table_number": payload.get("table_number") or payload.get("settlement_table"),
                "collective_bill_name": payload.get("collective_bill_name"),
                "order_number": payload.get("order_number"),
                "order_numbers": payload.get("order_numbers") or [],
                "waiter_name": payload.get("waiter_name"),
                "payment_types": [
                    str(p.get("type") or "")
                    for p in payload.get("payments") or []
                    if isinstance(p, dict) and p.get("type")
                ],
                "total_cents": paid_total,
                "item_count": item_count,
                "currency": ev.get("currency", "EUR"),
            }
        )
    return PaymentsListResponse(payments=payments)


@router.post("/v1/payments/{payment_id}/receipt", response_model=PaymentReceiptEscposResponse)
def payment_receipt(
    payment_id: int, body: PaymentReceiptBody | None = None, db: Session = Depends(get_db)
) -> PaymentReceiptEscposResponse:
    row = db.query(PaymentReceipt).filter(PaymentReceipt.id == payment_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    bundle = _get_bundle_dict(db)
    ev = _event_from_bundle(bundle, row.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    payload = json.loads(row.payload_json or "{}")
    esc = build_payment_receipt_text(
        payload,
        ev.get("name", "Event"),
        payment_id=row.id,
        articles=_article_map(ev),
        currency=ev.get("currency", "EUR"),
        reprint=bool(body and body.reprint),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return PaymentReceiptEscposResponse(
        payment_id=row.id,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
    )


@router.post("/v1/printers/test-receipt", response_model=EscposPayloadResponse)
def printer_test_receipt(
    body: PrinterTestReceiptBody | None = None, db: Session = Depends(get_db)
) -> EscposPayloadResponse:
    event_name = "Test"
    currency = "EUR"
    articles = {"1": {"id": 1, "name": "Testartikel", "price": 1.0, "additions": []}}
    event_id = body.event_id if body else None
    if event_id:
        bundle = _get_bundle_dict(db)
        ev = _event_from_bundle(bundle, event_id)
        if not ev:
            raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
        event_name = ev.get("name", "Event")
        currency = ev.get("currency", "EUR")
        articles = _article_map(ev) or articles
    payload = {
        "event_id": event_id,
        "table_number": 1,
        "waiter_name": "Test",
        "lines": [{"article_id": 1, "qty": 1, "article_name": "Testartikel", "note": "Bluetooth Test", "additions": []}],
        "payments": [{"type": "cash", "amount_cents": 100}],
        "payment_status": "paid",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
    esc = build_payment_receipt_text(
        payload,
        event_name,
        articles=articles,
        currency=currency,
        generated_at=payload["paid_at"],
    )
    return EscposPayloadResponse(escpos_payload=base64.b64encode(esc).decode("ascii"))


@router.get("/v1/print-jobs", response_model=list[PrintJobSummary])
def list_print_jobs(db: Session = Depends(get_db)) -> list[PrintJobSummary]:
    rows = db.query(PrintJob).order_by(PrintJob.id.desc()).limit(50).all()
    return [
        PrintJobSummary(
            id=r.id,
            local_order_id=r.local_order_id,
            printer_host=r.printer_host,
            status=r.status,
            last_error=r.last_error,
        )
        for r in rows
    ]
