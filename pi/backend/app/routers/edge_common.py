"""Shared constants and helpers for edge API route modules."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..domain.sync_enqueue import enrich_payload_for_cloud_sync, enqueue_payload_sync
from ..models import (
    CollectiveBill,
    EventPickupCounter,
    KitchenTicket,
    KitchenTicketLine,
    LocalOrder,
    OutboxEntry,
    PaymentReceipt,
    PrintJob,
)
from ..order_fiscal import waiter_name_from_event
from ..order_line_utils import discount_signature, line_key as _line_key
from ..pricing import (
    line_total_cents,
    line_unit_cents,
    normalize_discount,
    order_total_cents,
)
from ..printer_endpoint import parse_printer_host_entry, resolve_printer_endpoint
from ..printer_routing import resolve_endpoint_by_appliance, resolve_printer_target
from ..print_worker import (
    build_customer_pickup_text,
    build_escpos_receipt_text,
    build_payment_receipt_text,
    build_voucher_slip_text,
    resolve_station_uuid_for_line,
    station_name_from_event,
)
from ..vouchers import is_voucher_sale_line, order_lines_total_cents

PAYMENT_MODES_CASH = {"pay_now", "instant"}
ALLOWED_PAYMENT_TYPES = frozenset({"cash", "twint", "sumup", "stripe_terminal"})
STRIPE_PAYMENT_INTENT_ID_PATTERN = re.compile(r"^pi_[A-Za-z0-9_]+$")


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
        if t not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Payment type «{t or '?'}» is not allowed for this event",
            )
        if t == "stripe_terminal":
            pi_id = (p.get("stripe_payment_intent_id") or "").strip()
            if not STRIPE_PAYMENT_INTENT_ID_PATTERN.match(pi_id):
                raise HTTPException(
                    status_code=400,
                    detail="Stripe Terminal payment requires a valid stripe_payment_intent_id",
                )


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
    """Sum selection qty using discounted line_total_cents from open order line groups."""
    net_by_key: dict[tuple, tuple[int, int]] = {}
    for g in line_groups:
        key = _line_key(
            g["article_id"],
            g.get("note", ""),
            g.get("additions"),
            g.get("discount"),
        )
        total_qty = max(1, int(g.get("total_qty") or 1))
        line_total = int(g.get("line_total_cents") or 0)
        net_by_key[key] = (line_total, total_qty)
    total = 0
    for s in selections:
        if not isinstance(s, dict):
            continue
        qty = max(1, int(s.get("qty") or 1))
        key = _line_key(
            s.get("article_id"),
            s.get("note", ""),
            s.get("additions"),
            s.get("discount"),
        )
        entry = net_by_key.get(key)
        if entry is None:
            raise HTTPException(status_code=400, detail="Selection not found on open orders")
        line_total, total_qty = entry
        total += round(line_total / total_qty) * qty
    return total


def _build_line_groups_from_orders(orders: list, articles: dict) -> list[dict]:
    merged: dict[tuple, dict] = {}
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
            disc = normalize_discount(line.get("discount"))
            key = _line_key(aid, note, adds, disc)
            qty = max(1, int(line.get("qty") or 1))
            line_cents = line_total_cents(line, articles)
            unit = line_unit_cents(line, articles)
            if key not in merged:
                merged[key] = {
                    "article_id": int(aid),
                    "note": note,
                    "additions": adds,
                    "discount": disc,
                    "total_qty": 0,
                    "unit_cents": unit,
                    "line_total_cents": 0,
                }
            merged[key]["total_qty"] += qty
            merged[key]["line_total_cents"] += line_cents
    return sorted(
        merged.values(),
        key=lambda g: (
            g["article_id"],
            g["note"],
            _additions_signature(g.get("additions")),
            discount_signature(g.get("discount")),
        ),
    )


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
    host, port, feed_lines = resolve_printer_endpoint(ev, reg_uuid)
    esc = build_voucher_slip_text(
        event_name=ev.get("name", "Event"),
        voucher_name=voucher_name,
        value_cents=value_cents,
        currency=ev.get("currency", "EUR"),
        copy_index=copy_index,
        copy_total=copy_total,
        event=ev,
        feed_lines=feed_lines,
    )
    pj = PrintJob(
        local_order_id=order_id,
        station_uuid=reg_uuid,
        job_kind="voucher",
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

def _add_waiter_name(ev: dict, payload: dict) -> None:
    if payload.get("waiter_name"):
        return
    waiter_uuid = payload.get("waiter_uuid")
    if waiter_uuid:
        name = waiter_name_from_event(ev, waiter_uuid)
        if name:
            payload["waiter_name"] = name

def _station_config_for_uuid(ev: dict, station_uuid: str | None) -> dict | None:
    if station_uuid is None:
        return None
    for st in (ev.get("configuration") or {}).get("stations") or []:
        if str(st.get("uuid")) == str(station_uuid):
            return st
    return None


def _create_print_job_for_lines(
    db: Session,
    *,
    order_id: int,
    station_uuid: str | None,
    payload: dict,
    station_lines: list[dict],
    ev: dict,
    articles: dict,
    job_kind: str = "station_order",
    printer_appliance_id: int | None = None,
    table_number: int | None = None,
    pickup_code: str | None = None,
) -> int:
    station_payload = {**payload, "lines": station_lines}
    _add_waiter_name(ev, station_payload)
    station_label = station_name_from_event(ev, station_uuid)
    if printer_appliance_id is not None:
        host, port, feed_lines = resolve_endpoint_by_appliance(ev, printer_appliance_id)
    else:
        host, port, feed_lines, resolved_id = resolve_printer_target(
            ev,
            station_uuid,
            table_number=table_number if table_number is not None else payload.get("table_number"),
            pickup_code=pickup_code if pickup_code is not None else payload.get("pickup_code"),
        )
        printer_appliance_id = resolved_id
    esc = build_escpos_receipt_text(
        station_payload,
        ev.get("name", "Event"),
        station_name=station_label,
        articles=articles,
        local_order_id=order_id,
        currency=ev.get("currency", "EUR"),
        event=ev,
        feed_lines=feed_lines,
    )
    pj = PrintJob(
        local_order_id=order_id,
        station_uuid=station_uuid,
        job_kind=job_kind,
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
    host, port, feed_lines = resolve_printer_endpoint(ev, cash_register_uuid)
    esc = build_customer_pickup_text(
        station_payload,
        ev.get("name", "Event"),
        station_name=station_label,
        articles=articles,
        event=ev,
        local_order_id=order_id,
        currency=ev.get("currency", "EUR"),
        feed_lines=feed_lines,
    )
    pj = PrintJob(
        local_order_id=order_id,
        station_uuid=station_uuid,
        job_kind="customer_pickup",
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
    printer_appliance_id: int | None = None,
) -> int:
    ticket = KitchenTicket(
        local_order_id=order_id,
        event_id=event_id,
        station_uuid=station_uuid,
        printer_appliance_id=printer_appliance_id,
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
    payload = enrich_payload_for_cloud_sync(
        payload,
        local_order_id=order.id,
        session_id=int(order.session_id),
    )
    cid = order.client_order_id
    for out in (
        db.query(OutboxEntry)
        .filter(OutboxEntry.event_id == order.event_id, OutboxEntry.status.in_(("pending", "error")))
        .order_by(OutboxEntry.id.asc())
        .all()
    ):
        try:
            existing = json.loads(out.payload_json)
        except json.JSONDecodeError:
            continue
        if existing.get("client_order_id") == cid:
            out.payload_json = json.dumps(payload)
            out.status = "pending"
            return
    enqueue_payload_sync(db, event_id=order.event_id, client_order_id=cid, payload=payload)
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
    from ..shift_integration import record_shift_for_payment_receipt

    record_shift_for_payment_receipt(
        db,
        ev,
        receipt_payload,
        event_id=int(receipt_payload.get("event_id") or ev.get("id") or 0),
        reference_id=str(source_id) if source_id is not None else None,
    )
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


def _printer_host_configured(ev: dict, target_uuid: str) -> bool:
    """True when printer_hosts has an explicit non-empty host for this uuid."""
    hosts = ev.get("printer_hosts") or {}
    key = str(target_uuid).strip()
    if key not in hosts:
        return False
    entry = parse_printer_host_entry(hosts[key])
    return bool(entry.get("host"))


def _local_order_id_for_payment_receipt(row: PaymentReceipt) -> int:
    """PrintJob requires local_order_id; use settlement order when recorded on receipt."""
    if row.source_type in ("order", "table_partial") and row.source_id:
        try:
            return int(row.source_id)
        except (TypeError, ValueError):
            pass
    return 0


def _create_payment_receipt_print_job(
    db: Session,
    row: PaymentReceipt,
    ev: dict,
    station_uuid: str,
) -> int:
    payload = json.loads(row.payload_json or "{}")
    host, port, feed_lines = resolve_printer_endpoint(ev, station_uuid)
    esc = build_payment_receipt_text(
        payload,
        ev.get("name", "Event"),
        payment_id=row.id,
        articles=_article_map(ev),
        currency=ev.get("currency", "EUR"),
        generated_at=datetime.now(timezone.utc).isoformat(),
        event=ev,
        feed_lines=feed_lines,
    )
    pj = PrintJob(
        local_order_id=_local_order_id_for_payment_receipt(row),
        station_uuid=station_uuid,
        job_kind="payment_receipt",
        printer_host=host,
        printer_port=port,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
        status="queued",
    )
    db.add(pj)
    db.flush()
    return pj.id


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
        order_discount = payload.get("order_discount")
        line_cents = order_total_cents(lines, order_discount, ev, arts)
        _, line_qty = _line_totals(lines, arts)
        total_cents += line_cents
        item_count += line_qty
        entry = {
            "local_order_id": o.id,
            "client_order_id": o.client_order_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "lines": lines,
            "line_total_cents": line_cents,
        }
        if order_discount:
            entry["order_discount"] = order_discount
        open_orders.append(entry)
    line_groups = _build_line_groups_from_orders(orders, arts)
    return {
        **extra,
        "currency": ev.get("currency", "EUR"),
        "open_orders": open_orders,
        "line_groups": line_groups,
        "total_cents": total_cents,
        "item_count": item_count,
    }
