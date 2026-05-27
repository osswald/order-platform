"""ESC/POS builder, plain-text vouchers, print worker (network or file)."""

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import LocalOrder, PrintJob, SyncedBundle

log = logging.getLogger(__name__)


def resolve_station_uuid_for_line(ev: dict, line: dict) -> str | None:
    su = line.get("station_uuid")
    if su is not None and str(su).strip():
        return str(su).strip()
    aid = line.get("article_id")
    if aid is None:
        return None
    stations = (ev.get("configuration") or {}).get("stations") or []
    aid_n = int(aid)
    for st in stations:
        ids = [int(x) for x in (st.get("article_ids") or [])]
        if aid_n in ids:
            u = st.get("uuid")
            return str(u).strip() if u else None
    return None


def group_lines_by_station(ev: dict, lines: list) -> dict[str | None, list]:
    groups: dict[str | None, list] = {}
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        su = resolve_station_uuid_for_line(ev, line)
        groups.setdefault(su, []).append(dict(line))
    if not groups:
        groups[None] = []
    return groups


def station_name_from_event(ev: dict, station_uuid: str | None) -> str:
    if station_uuid is None:
        return "Standard"
    for st in (ev.get("configuration") or {}).get("stations") or []:
        if str(st.get("uuid")) == str(station_uuid):
            return str(st.get("name") or f"Station {station_uuid[:8]}")
    return f"Station {station_uuid[:8]}…"


def _article_map(ev: dict) -> dict:
    return ev.get("articles") or {}


def _price_hint_eur(cents: int) -> str:
    if cents == 0:
        return ""
    return f" ({cents / 100:.2f})"


def _money(cents: int, currency: str) -> str:
    return f"{cents / 100:.2f} {currency}"


def _payment_type_label(payment_type: str) -> str:
    labels = {
        "cash": "Bar",
        "twint": "TWINT",
        "sumup": "SumUp",
        "stripe_terminal": "Karte",
        "instant": "Sofort",
    }
    key = str(payment_type or "").lower()
    return labels.get(key, key or "Zahlung")


def build_payment_receipt_text(
    payload: dict,
    event_name: str,
    *,
    payment_id: int | None = None,
    articles: dict | None = None,
    currency: str = "EUR",
    reprint: bool = False,
    generated_at: str | None = None,
) -> bytes:
    """Build a basic ESC/POS receipt for Android Bluetooth transport."""
    from .pricing import line_total_cents

    arts = articles or {}
    lines = payload.get("lines") or []
    payments = payload.get("payments") or []
    item_total = sum(line_total_cents(line, arts) for line in lines if isinstance(line, dict))
    payment_total = sum(int(p.get("amount_cents") or 0) for p in payments if isinstance(p, dict))
    total = payment_total or item_total

    out: list[bytes] = []
    out.append(b"\x1b\x40")
    out.append(b"\x1b!\x20")
    out.append(b"Beleg\n")
    out.append(b"\x1b!\x00")
    if reprint:
        out.append(b"Kopie / Nachdruck\n")
    out.append(f"{event_name}\n".encode("utf-8", errors="replace"))
    if payment_id is not None:
        out.append(f"Beleg-ID: {payment_id}\n".encode("utf-8", errors="replace"))
    table = payload.get("table_number") or payload.get("settlement_table")
    if table:
        out.append(f"Tisch: {table}\n".encode("utf-8", errors="replace"))
    coll_name = payload.get("collective_bill_name")
    if coll_name:
        out.append(f"Sammelrechnung: {coll_name}\n".encode("utf-8", errors="replace"))
    pickup_code = payload.get("pickup_code")
    if pickup_code:
        out.append(f"Pickup: {pickup_code}\n".encode("utf-8", errors="replace"))
    waiter_name = payload.get("waiter_name")
    if waiter_name:
        out.append(f"Kellner: {waiter_name}\n".encode("utf-8", errors="replace"))
    order_no = payload.get("order_number")
    if order_no is not None:
        out.append(f"Bestellung #{order_no}\n".encode("utf-8", errors="replace"))
    paid_at = payload.get("paid_at") or payload.get("settled_at") or payload.get("ordered_at") or generated_at
    if paid_at:
        out.append(f"Zeit: {paid_at}\n".encode("utf-8", errors="replace"))
    out.append(b"---\n")

    for line in lines:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        qty = max(1, int(line.get("qty") or 1))
        art = arts.get(str(aid)) or arts.get(int(aid)) or {}
        name = line.get("article_name") or art.get("name") or f"#{aid}"
        cents = line_total_cents(line, arts)
        out.append(f"{qty}x {name} {_money(cents, currency)}\n".encode("utf-8", errors="replace"))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = add.get("name") or f"Zusatz #{add.get('article_id')}"
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            hint = f" {_money(add_cents, currency)}" if add_cents else ""
            out.append(f"  + {add_qty}x {add_name}{hint}\n".encode("utf-8", errors="replace"))
        note = (line.get("note") or "").strip()
        if note:
            out.append(f"  {note}\n".encode("utf-8", errors="replace"))

    out.append(b"---\n")
    out.append(f"Total: {_money(total, currency)}\n".encode("utf-8", errors="replace"))
    for payment in payments:
        if not isinstance(payment, dict):
            continue
        label = _payment_type_label(str(payment.get("type") or ""))
        amount = int(payment.get("amount_cents") or 0)
        out.append(f"{label}: {_money(amount, currency)}\n".encode("utf-8", errors="replace"))
    out.append(b"\nDanke!\n\n\n\x1dV\x00")
    return b"".join(out)


def build_voucher_slip_text(
    *,
    event_name: str,
    voucher_name: str,
    value_cents: int,
    currency: str = "EUR",
    copy_index: int | None = None,
    copy_total: int | None = None,
    generated_at: str | None = None,
) -> bytes:
    """Customer-facing amount voucher slip (one per purchased unit)."""
    out: list[bytes] = []
    out.append(b"\x1b\x40")
    out.append(b"\x1b!\x20")
    out.append(b"GUTSCHEIN\n")
    out.append(b"\x1b!\x00")
    out.append(f"{event_name}\n".encode("utf-8", errors="replace"))
    out.append(f"{voucher_name}\n".encode("utf-8", errors="replace"))
    out.append(f"Wert: {_money(value_cents, currency)}\n".encode("utf-8", errors="replace"))
    if copy_index is not None and copy_total is not None and copy_total > 1:
        out.append(f"Kopie {copy_index}/{copy_total}\n".encode("utf-8", errors="replace"))
    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    out.append(f"{ts}\n".encode("utf-8", errors="replace"))
    out.append(b"\nEinloesung bei Zahlung.\n\n\n\x1dV\x00")
    return b"".join(out)


def build_escpos_receipt_text(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
) -> bytes:
    from .pricing import line_total_cents

    arts = articles or {}
    lines_out: list[bytes] = []
    lines_out.append(b"\x1b\x40")
    lines_out.append(f"{event_name}\n".encode("utf-8", errors="replace"))
    if station_name:
        lines_out.append(f"Station: {station_name}\n".encode("utf-8", errors="replace"))
    table = payload.get("table_number")
    pickup_code = payload.get("pickup_code")
    if pickup_code:
        lines_out.append(f"Pickup: {pickup_code}\n".encode("utf-8", errors="replace"))
    elif table is not None and int(table or 0) > 0:
        lines_out.append(f"Tisch: {table}\n".encode("utf-8", errors="replace"))
    wn = payload.get("waiter_name")
    if wn:
        lines_out.append(f"Kellner: {wn}\n".encode("utf-8", errors="replace"))
    order_no = payload.get("order_number")
    if order_no is not None:
        lines_out.append(f"Bestellung #{order_no}\n".encode("utf-8", errors="replace"))
    ordered_at = payload.get("ordered_at")
    if ordered_at:
        lines_out.append(f"Zeit: {ordered_at}\n".encode("utf-8", errors="replace"))
    lines_out.append(b"---\n")
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        qty = max(1, int(line.get("qty") or 1))
        art = arts.get(str(aid)) or arts.get(int(aid)) or {}
        name = line.get("article_name") or art.get("name") or f"#{aid}"
        cents = line_total_cents(line, arts)
        lines_out.append(f"{qty}x {name}{_price_hint_eur(cents)}\n".encode("utf-8", errors="replace"))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = add.get("name") or f"Zusatz #{add.get('article_id')}"
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            lines_out.append(f"  + {add_qty}x {add_name}{_price_hint_eur(add_cents)}\n".encode("utf-8", errors="replace"))
        note = (line.get("note") or "").strip()
        if note:
            lines_out.append(f"  {note}\n".encode("utf-8", errors="replace"))
    lines_out.append(b"\n\n\n\x1dV\x00")
    return b"".join(lines_out)


def build_customer_pickup_text(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
) -> bytes:
    from .pricing import line_total_cents

    arts = articles or {}
    lines_out: list[bytes] = []
    lines_out.append(b"\x1b\x40")
    lines_out.append(b"\x1b!\x20")
    lines_out.append(f"Pickup {payload.get('pickup_code') or '?'}\n".encode("utf-8", errors="replace"))
    lines_out.append(b"\x1b!\x00")
    lines_out.append(f"{event_name}\n".encode("utf-8", errors="replace"))
    if station_name:
        lines_out.append(f"Station: {station_name}\n".encode("utf-8", errors="replace"))
    ordered_at = payload.get("ordered_at")
    if ordered_at:
        lines_out.append(f"Zeit: {ordered_at}\n".encode("utf-8", errors="replace"))
    lines_out.append(b"Bezahlt\n---\n")
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        qty = max(1, int(line.get("qty") or 1))
        art = arts.get(str(aid)) or arts.get(int(aid)) or {}
        name = line.get("article_name") or art.get("name") or f"#{aid}"
        cents = line_total_cents(line, arts)
        lines_out.append(f"{qty}x {name}{_price_hint_eur(cents)}\n".encode("utf-8", errors="replace"))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = add.get("name") or f"Zusatz #{add.get('article_id')}"
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            lines_out.append(f"  + {add_qty}x {add_name}{_price_hint_eur(add_cents)}\n".encode("utf-8", errors="replace"))
        note = (line.get("note") or "").strip()
        if note:
            lines_out.append(f"  {note}\n".encode("utf-8", errors="replace"))
    lines_out.append(b"\nBitte an der Ausgabe abholen.\n\n\n\x1dV\x00")
    return b"".join(lines_out)


def _parse_host_port(host_port: str, default_port: int = 9100) -> tuple[str, int]:
    if ":" in host_port:
        host, _, port_s = host_port.rpartition(":")
        try:
            return host.strip(), int(port_s)
        except ValueError:
            return host_port.strip(), default_port
    return host_port.strip(), default_port


async def _send_to_printer(host: str, port: int, data: bytes) -> None:
    print_to_file = os.getenv("PRINT_TO_FILE", "").strip()
    if print_to_file:
        out_dir = Path(os.getenv("PRINT_OUTPUT_DIR", "/data/print-vouchers"))
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\-.]", "_", f"{host}_{port}")
        path = out_dir / f"{safe}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.bin"
        path.write_bytes(data)
        return
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(data)
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


def _load_event_for_order(db: Session, order: LocalOrder) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    try:
        bundle = json.loads(row.json_body)
    except json.JSONDecodeError:
        return None
    for ev in bundle.get("events", []) or []:
        if int(ev.get("id")) == int(order.event_id):
            return ev
    return None


async def process_print_job(db: Session, job: PrintJob, ev: dict | None) -> None:
    esc = base64.b64decode(job.escpos_payload)
    await _send_to_printer(job.printer_host, job.printer_port, esc)
    job.status = "sent"
    job.last_error = None


async def print_worker_loop(stop_event: asyncio.Event) -> None:
    """Poll queued print jobs."""
    log.info("Print worker started")
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            jobs = (
                db.query(PrintJob)
                .filter(PrintJob.status == "queued")
                .order_by(PrintJob.id.asc())
                .limit(10)
                .all()
            )
            for job in jobs:
                order = db.query(LocalOrder).filter(LocalOrder.id == job.local_order_id).first()
                ev = _load_event_for_order(db, order) if order else None
                try:
                    await process_print_job(db, job, ev)
                except Exception as e:
                    job.status = "error"
                    job.last_error = str(e)[:2000]
                    log.exception("print job %s failed", job.id)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("print worker tick failed")
        finally:
            db.close()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
    log.info("Print worker stopped")


def run_print_job_sync(db: Session, job_id: int) -> None:
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        return
    order = db.query(LocalOrder).filter(LocalOrder.id == job.local_order_id).first()
    ev = _load_event_for_order(db, order) if order else None
    asyncio.run(process_print_job(db, job, ev))
