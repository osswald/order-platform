"""ESC/POS builder, plain-text vouchers, print worker (network ESC/POS)."""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import LocalOrder, PrintJob, SyncedBundle
from .pricing import addition_display_name

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


def _escpos_encoding() -> str:
    return os.getenv("ESCPOS_ENCODING", "cp858").strip() or "cp858"


def _escpos_codepage() -> int:
    raw = os.getenv("ESCPOS_CODEPAGE", "19").strip()
    try:
        return int(raw)
    except ValueError:
        return 19


def _escpos_init() -> bytes:
    return b"\x1b\x40" + bytes([0x1B, 0x74, _escpos_codepage() & 0xFF]) + _escpos_reset_style()


def _escpos_text(text: str) -> bytes:
    return str(text).encode(_escpos_encoding(), errors="replace")


def _escpos_ln(text: str) -> bytes:
    return _escpos_text(text) + b"\n"


def _escpos_align(mode: int) -> bytes:
    """0=left, 1=center, 2=right."""
    return bytes([0x1B, 0x61, mode & 0xFF])


def _escpos_bold(on: bool = True) -> bytes:
    """ESC E — emphasized / bold (Epson-compatible)."""
    return bytes([0x1B, 0x45, 1 if on else 0])


def _escpos_char_size(width_mult: int = 1, height_mult: int = 1) -> bytes:
    """GS ! — character width/height multiplier 1–8 (Epson)."""
    w = max(1, min(8, width_mult))
    h = max(1, min(8, height_mult))
    n = (w - 1) | ((h - 1) << 4)
    return bytes([0x1D, 0x21, n])


def _escpos_font(
    *,
    double_height: bool = False,
    double_width: bool = False,
    bold: bool = False,
) -> bytes:
    flags = 0
    if bold:
        flags |= 0x08
    if double_height:
        flags |= 0x10
    if double_width:
        flags |= 0x20
    return bytes([0x1B, 0x21, flags])


def _escpos_reset_style() -> bytes:
    return _escpos_font() + _escpos_char_size(1, 1) + _escpos_bold(False)


def _escpos_hero_scale() -> int:
    raw = os.getenv("ESCPOS_HERO_SCALE", "8").strip()
    try:
        return max(2, min(8, int(raw)))
    except ValueError:
        return 8


def _escpos_hero_style() -> bytes:
    """Maximize table/pickup: GS ! magnification (default 8×) plus bold double-size."""
    scale = _escpos_hero_scale()
    return (
        _escpos_char_size(scale, scale)
        + _escpos_font(double_height=True, double_width=True, bold=True)
        + _escpos_bold(True)
    )


def _escpos_subline(text: str, *, indent: int = 2) -> bytes:
    """Indented line without price column (additions, notes)."""
    return _escpos_ln(f"{' ' * indent}{text}")


def _escpos_append_hero(lines_out: list[bytes], hero: str) -> None:
    lines_out.append(_escpos_align(1))
    lines_out.append(_escpos_hero_style())
    lines_out.append(_escpos_ln(hero))
    lines_out.append(b"\n")
    lines_out.append(_escpos_reset_style())
    lines_out.append(_escpos_align(0))


def _escpos_cut() -> bytes:
    return b"\n\n\n\x1dV\x00"


def _escpos_line_width() -> int:
    raw = os.getenv("ESCPOS_LINE_WIDTH", "48").strip()
    try:
        return max(24, int(raw))
    except ValueError:
        return 48


def _escpos_timezone() -> ZoneInfo:
    name = os.getenv("ESCPOS_TIMEZONE", "Europe/Zurich").strip() or "Europe/Zurich"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Europe/Zurich")


def _escpos_format_ordered_at(iso: str | None) -> str:
    if not iso:
        dt = datetime.now(timezone.utc)
    else:
        s = str(iso).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(_escpos_timezone())
    return local.strftime("%d.%m.%Y %H:%M Uhr")


def _escpos_rule(width: int | None = None) -> bytes:
    w = width if width is not None else _escpos_line_width()
    return _escpos_ln("-" * w)


def _escpos_two_column(
    left: str,
    right: str,
    width: int | None = None,
    *,
    left_bold: bool = False,
) -> bytes:
    w = width if width is not None else _escpos_line_width()
    right = right or ""
    left = left or ""
    max_left = max(0, w - len(right) - 1)
    if len(left) > max_left:
        if max_left > 1:
            left = left[: max_left - 1] + "…"
        else:
            left = left[:max_left]
    pad = w - len(left) - len(right)
    if pad < 1:
        pad = 1
    out: list[bytes] = []
    if left_bold:
        out.append(_escpos_bold(True))
    out.append(_escpos_text(left))
    if left_bold:
        out.append(_escpos_bold(False))
    out.append(_escpos_text(" " * pad + right))
    out.append(b"\n")
    return b"".join(out)


def _escpos_item_row(
    qty: int,
    name: str,
    cents: int,
    width: int | None = None,
    *,
    indent: int = 0,
) -> bytes:
    w = width if width is not None else _escpos_line_width()
    price = f"{cents / 100:.2f}"
    if qty > 0:
        left = f"{' ' * indent}{qty} {name}".strip()
    else:
        left = f"{' ' * indent}{name}".strip()
    max_left = max(0, w - len(price) - 1)
    if len(left) > max_left:
        if max_left > 1:
            left = left[: max_left - 1] + "…"
        else:
            left = left[:max_left]
    pad = w - len(left) - len(price)
    if pad < 1:
        pad = 1
    line = left + (" " * pad) + price
    if len(line) > w:
        line = line[:w]
    return _escpos_ln(line)


def _format_order_ids(
    order_number: int | None, local_order_id: int | None
) -> str:
    parts: list[str] = []
    if order_number is not None:
        parts.append(f"Best #{int(order_number):05d}")
    if local_order_id is not None:
        parts.append(f"Bon #{int(local_order_id):06d}")
    return " | ".join(parts)


def _line_base_total_cents(line: dict, arts: dict) -> int:
    """Article line total excluding additions (for split slip rows)."""
    from .pricing import _article_entry

    qty = max(1, int(line.get("qty") or 1))
    if line.get("unit_cents") is not None:
        unit = int(line["unit_cents"])
    else:
        aid = line.get("article_id")
        base = _article_entry(arts, aid)
        price = float(base["price"]) if base and base.get("price") is not None else 0.0
        unit = int(round(price * 100))
    return unit * qty


def _append_escpos_order_lines_formatted(
    lines_out: list[bytes],
    payload: dict,
    arts: dict,
    currency: str,
    width: int,
) -> tuple[int, int]:
    """Append item rows; return (total_qty, total_cents)."""
    from .pricing import line_total_cents

    total_qty = 0
    total_cents = 0
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        qty = max(1, int(line.get("qty") or 1))
        art = arts.get(str(aid)) or arts.get(int(aid)) or {}
        name = line.get("article_name") or art.get("name") or f"#{aid}"
        base_cents = _line_base_total_cents(line, arts)
        total_qty += qty
        total_cents += line_total_cents(line, arts)
        lines_out.append(_escpos_item_row(qty, name, base_cents, width))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = addition_display_name(add, arts, art)
            if add_qty > 1:
                lines_out.append(_escpos_subline(f"{add_qty} + {add_name}"))
            else:
                lines_out.append(_escpos_subline(f"+ {add_name}"))
        note = (line.get("note") or "").strip()
        if note:
            lines_out.append(_escpos_subline(note))
    return total_qty, total_cents


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
    out.append(_escpos_init())
    out.append(_escpos_font(double_width=True))
    out.append(_escpos_ln("Beleg"))
    out.append(_escpos_font())
    if reprint:
        out.append(_escpos_ln("Kopie / Nachdruck"))
    out.append(_escpos_ln(event_name))
    if payment_id is not None:
        out.append(_escpos_ln(f"Beleg-ID: {payment_id}"))
    table = payload.get("table_number") or payload.get("settlement_table")
    if table:
        out.append(_escpos_ln(f"Tisch: {table}"))
    coll_name = payload.get("collective_bill_name")
    if coll_name:
        out.append(_escpos_ln(f"Sammelrechnung: {coll_name}"))
    pickup_code = payload.get("pickup_code")
    if pickup_code:
        out.append(_escpos_ln(f"Pickup: {pickup_code}"))
    waiter_name = payload.get("waiter_name")
    if waiter_name:
        out.append(_escpos_ln(f"Kellner: {waiter_name}"))
    order_no = payload.get("order_number")
    if order_no is not None:
        out.append(_escpos_ln(f"Bestellung #{order_no}"))
    paid_at = payload.get("paid_at") or payload.get("settled_at") or payload.get("ordered_at") or generated_at
    if paid_at:
        out.append(_escpos_ln(f"Zeit: {paid_at}"))
    out.append(_escpos_ln("---"))

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
        out.append(_escpos_ln(f"{qty}x {name} {_money(cents, currency)}"))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = addition_display_name(add, arts, art)
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            hint = f" {_money(add_cents, currency)}" if add_cents else ""
            out.append(_escpos_ln(f"  + {add_qty}x {add_name}{hint}"))
        note = (line.get("note") or "").strip()
        if note:
            out.append(_escpos_ln(f"  {note}"))

    out.append(_escpos_ln("---"))
    out.append(_escpos_ln(f"Total: {_money(total, currency)}"))
    for payment in payments:
        if not isinstance(payment, dict):
            continue
        label = _payment_type_label(str(payment.get("type") or ""))
        amount = int(payment.get("amount_cents") or 0)
        out.append(_escpos_ln(f"{label}: {_money(amount, currency)}"))
    out.append(_escpos_ln(""))
    out.append(_escpos_ln("Danke!"))
    out.append(_escpos_cut())
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
    out.append(_escpos_init())
    out.append(_escpos_font(double_width=True))
    out.append(_escpos_ln("GUTSCHEIN"))
    out.append(_escpos_font())
    out.append(_escpos_ln(event_name))
    out.append(_escpos_ln(voucher_name))
    out.append(_escpos_ln(f"Wert: {_money(value_cents, currency)}"))
    if copy_index is not None and copy_total is not None and copy_total > 1:
        out.append(_escpos_ln(f"Kopie {copy_index}/{copy_total}"))
    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    out.append(_escpos_ln(ts))
    out.append(_escpos_ln(""))
    out.append(_escpos_ln("Einlösung bei Zahlung."))
    out.append(_escpos_cut())
    return b"".join(out)


def build_escpos_receipt_text(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
    local_order_id: int | None = None,
    currency: str = "EUR",
) -> bytes:
    """Station kitchen/order slip (reference layout)."""
    arts = articles or {}
    width = _escpos_line_width()
    lines_out: list[bytes] = []
    lines_out.append(_escpos_init())
    lines_out.append(_escpos_align(0))

    ordered_at = _escpos_format_ordered_at(payload.get("ordered_at"))
    lines_out.append(_escpos_two_column(event_name, ordered_at, width, left_bold=True))

    station_label = f"Station: {station_name}" if station_name else "Station:"
    order_number = payload.get("order_number")
    ids_right = _format_order_ids(
        int(order_number) if order_number is not None else None,
        local_order_id,
    )
    lines_out.append(_escpos_two_column(station_label, ids_right, width))

    lines_out.append(_escpos_rule(width))

    table = payload.get("table_number")
    pickup_code = payload.get("pickup_code")
    hero: str | None = None
    if table is not None and int(table or 0) > 0:
        hero = str(int(table))
    elif pickup_code:
        hero = str(pickup_code)

    if hero:
        _escpos_append_hero(lines_out, hero)

    lines_out.append(_escpos_rule(width))
    total_qty, total_cents = _append_escpos_order_lines_formatted(
        lines_out, payload, arts, currency, width
    )
    lines_out.append(_escpos_rule(width))
    total_price = f"{total_cents / 100:.2f}"
    lines_out.append(_escpos_two_column(str(total_qty), f"{currency} {total_price}", width))

    wn = (payload.get("waiter_name") or "").strip()
    lines_out.append(_escpos_align(1))
    lines_out.append(_escpos_ln("Danke für Ihre Bestellung!"))
    if wn:
        lines_out.append(_escpos_ln(wn))
    lines_out.append(_escpos_align(0))
    lines_out.append(_escpos_cut())
    return b"".join(lines_out)


def _append_escpos_order_lines(lines_out: list[bytes], payload: dict, arts: dict) -> None:
    from .pricing import line_total_cents

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
        lines_out.append(_escpos_ln(f"{qty}x {name}{_price_hint_eur(cents)}"))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = addition_display_name(add, arts, art)
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            lines_out.append(_escpos_ln(f"  + {add_qty}x {add_name}{_price_hint_eur(add_cents)}"))
        note = (line.get("note") or "").strip()
        if note:
            lines_out.append(_escpos_ln(f"  {note}"))


def build_escpos_station_test_slip(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
) -> bytes:
    """Admin Testdruck: font sizes, center alignment, and accent character demo."""
    arts = articles or {}
    accent_demo = "Ää Öö Üü ß  Éé Èè Îî Çç"
    out: list[bytes] = []
    out.append(_escpos_init())
    out.append(_escpos_align(1))
    out.append(_escpos_font(double_height=True, double_width=True))
    out.append(_escpos_ln("Testdruck"))
    out.append(_escpos_font())
    out.append(_escpos_ln(accent_demo))
    out.append(_escpos_align(0))
    out.append(_escpos_ln(event_name))
    if station_name:
        out.append(_escpos_ln(f"Station: {station_name}"))
    wn = payload.get("waiter_name")
    if wn:
        out.append(_escpos_ln(f"Kellner: {wn}"))
    ordered_at = payload.get("ordered_at")
    if ordered_at:
        out.append(_escpos_ln(f"Zeit: {ordered_at}"))
    if station_name:
        out.append(_escpos_font(double_height=True))
        out.append(_escpos_ln(station_name))
        out.append(_escpos_font())
    out.append(_escpos_font(double_width=True))
    out.append(_escpos_ln("Breit"))
    out.append(_escpos_font())
    out.append(_escpos_ln("---"))
    _append_escpos_order_lines(out, payload, arts)
    out.append(_escpos_cut())
    return b"".join(out)


def build_customer_pickup_text(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
) -> bytes:
    arts = articles or {}
    lines_out: list[bytes] = []
    lines_out.append(_escpos_init())
    lines_out.append(_escpos_font(double_width=True))
    lines_out.append(_escpos_ln(f"Pickup {payload.get('pickup_code') or '?'}"))
    lines_out.append(_escpos_font())
    lines_out.append(_escpos_ln(event_name))
    if station_name:
        lines_out.append(_escpos_ln(f"Station: {station_name}"))
    ordered_at = payload.get("ordered_at")
    if ordered_at:
        lines_out.append(_escpos_ln(f"Zeit: {ordered_at}"))
    lines_out.append(_escpos_ln("Bezahlt"))
    lines_out.append(_escpos_ln("---"))
    _append_escpos_order_lines(lines_out, payload, arts)
    lines_out.append(_escpos_ln(""))
    lines_out.append(_escpos_ln("Bitte an der Ausgabe abholen."))
    lines_out.append(_escpos_cut())
    return b"".join(lines_out)


def _effective_printer_host(host: str) -> str:
    override = os.getenv("ESCPOS_PRINTER_HOST_OVERRIDE", "").strip()
    return override if override else host


def _parse_host_port(host_port: str, default_port: int = 9100) -> tuple[str, int]:
    if ":" in host_port:
        host, _, port_s = host_port.rpartition(":")
        try:
            return host.strip(), int(port_s)
        except ValueError:
            return host_port.strip(), default_port
    return host_port.strip(), default_port


async def _send_to_printer(host: str, port: int, data: bytes) -> None:
    target_host = _effective_printer_host(host)
    reader, writer = await asyncio.open_connection(target_host, port)
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
