"""ESC/POS builder, vouchers, print worker (network ESC/POS)."""

import asyncio
import base64
import json
import logging
import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from escpos.printer import Dummy
from sqlalchemy.orm import Session

from .database import SessionLocal
from .emulated_printer import is_emulated_printer_mode, store_emulated_receipt
from .escpos_render import (
    encode_escpos_text,
    escpos_env_line_width,
    escpos_init_preamble,
    render_slip,
    resolve_line_width,
    resolve_logo_max_width,
    write_centered_block,
    write_centered_sized,
    write_centered_small_block,
    write_hero,
    write_item_row,
    write_line,
    write_logo_from_event,
    write_separator,
    write_sized_line,
    write_subline,
    write_two_column,
)
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


def _price_hint_eur(cents: int) -> str:
    if cents == 0:
        return ""
    return f" ({cents / 100:.2f})"


def _money(cents: int, currency: str) -> str:
    return f"{currency} {cents / 100:.2f}"


def _amount(cents: int) -> str:
    return f"{cents / 100:.2f}"


def _printing_block(ev: dict | None) -> dict:
    if not ev:
        return {}
    return (ev.get("configuration") or {}).get("printing") or {}


def _profile_cfg(ev: dict | None, profile_key: str) -> dict:
    block = _printing_block(ev)
    raw = block.get(profile_key) or {}
    return raw if isinstance(raw, dict) else {}


def _event_title_for_print(ev: dict | None, event_name: str) -> str:
    block = _printing_block(ev)
    label = (block.get("label_event_title") or "").strip()
    return label or event_name


def _escpos_line_width() -> int:
    return escpos_env_line_width()


def _escpos_timezone() -> ZoneInfo:
    name = os.getenv("ESCPOS_TIMEZONE", "Europe/Zurich").strip() or "Europe/Zurich"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Europe/Zurich")


def _format_ordered_at(iso: str | None) -> str:
    if not iso:
        dt = datetime.now(UTC)
    else:
        s = str(iso).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(_escpos_timezone())
    return local.strftime("%d.%m.%Y %H:%M Uhr")


def _format_order_ids(order_number: int | None, local_order_id: int | None) -> str:
    parts: list[str] = []
    if order_number is not None:
        parts.append(f"Best #{int(order_number):05d}")
    if local_order_id is not None:
        parts.append(f"Bon #{int(local_order_id):06d}")
    return " | ".join(parts)


def _station_operator_label(body: dict) -> str:
    """Kellner- oder Kassenname für Stationsbons (ohne Cloud-Fußzeile)."""
    source = (body.get("order_source") or "waiter").strip().lower()
    if source == "cash_register":
        reg = (body.get("cash_register_name") or "").strip()
        if reg:
            return reg
    return (body.get("waiter_name") or "").strip()


def _line_base_total_cents(line: dict, arts: dict) -> int:
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


def _escpos_text(text: str) -> bytes:
    return encode_escpos_text(text)


def _escpos_init() -> bytes:
    return escpos_init_preamble()


def _escpos_format_ordered_at(iso: str | None) -> str:
    return _format_ordered_at(iso)


def _payment_type_label(payment_type: str) -> str:
    labels = {
        "cash": "Bar",
        "twint": "TWINT",
        "sumup": "SumUp",
        "stripe_terminal": "Karte",
    }
    key = str(payment_type or "").lower()
    return labels.get(key, key or "Zahlung")


def _write_order_lines(
    printer: Dummy,
    payload: dict,
    arts: dict,
    *,
    show_prices: bool = True,
    currency: str = "EUR",
    line_size: str = "normal",
    width: int = 48,
    amount_with_currency: bool = True,
) -> None:
    from .pricing import line_total_cents

    align_prices = show_prices and (line_size or "normal").lower() == "normal"

    def _format_price(cents: int) -> str:
        return _money(cents, currency) if amount_with_currency else _amount(cents)

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
        if align_prices:
            write_two_column(printer, f"{qty}x {name}", _format_price(cents), width)
        else:
            price = _format_price(cents) if show_prices else _price_hint_eur(cents)
            write_sized_line(printer, f"{qty}x {name}{price}", line_size)
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = addition_display_name(add, arts, art)
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            add_left = f"  + {add_qty}x {add_name}" if add_qty > 1 else f"  + {add_name}"
            if align_prices and add_cents:
                write_two_column(printer, add_left, _format_price(add_cents), width)
            elif show_prices and add_cents:
                write_sized_line(printer, f"{add_left} {_format_price(add_cents)}", line_size)
            elif not show_prices:
                add_price = _price_hint_eur(add_cents)
                write_sized_line(printer, f"{add_left}{add_price}", line_size)
            else:
                write_sized_line(printer, add_left, line_size)
        note = (line.get("note") or "").strip()
        if note:
            write_sized_line(printer, f"  {note}", line_size)


def _write_payment_order_lines(
    printer: Dummy,
    payload: dict,
    arts: dict,
    event: dict | None,
    *,
    currency: str = "EUR",
    line_size: str = "normal",
    width: int = 48,
) -> None:
    from .discounts import discount_hint
    from .pricing import line_gross_cents, line_total_cents
    from .vouchers import is_voucher_sale_line, voucher_definition_by_uuid, voucher_sale_unit_cents

    align_prices = (line_size or "normal").lower() == "normal"
    ev = event or {}

    def _format_price(cents: int) -> str:
        return _amount(cents)

    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        if is_voucher_sale_line(line):
            qty = max(1, int(line.get("qty") or 1))
            v_uuid = str(line.get("voucher_definition_uuid") or "").strip()
            vd = voucher_definition_by_uuid(ev, v_uuid)
            name = (vd or {}).get("name") or "Gutschein"
            cents = voucher_sale_unit_cents(ev, line) * qty
            if align_prices:
                write_two_column(printer, f"{qty}x {name}", _format_price(cents), width)
            else:
                write_sized_line(printer, f"{qty}x {name} {_format_price(cents)}", line_size)
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        qty = max(1, int(line.get("qty") or 1))
        art = arts.get(str(aid)) or arts.get(int(aid)) or {}
        name = line.get("article_name") or art.get("name") or f"#{aid}"
        gross_cents = line_gross_cents(line, arts)
        cents = line_total_cents(line, arts)
        if align_prices:
            write_two_column(printer, f"{qty}x {name}", _format_price(cents), width)
        else:
            write_sized_line(printer, f"{qty}x {name} {_format_price(cents)}", line_size)
        hint = discount_hint(line.get("discount"), gross_cents, cents)
        if hint:
            write_subline(printer, hint, size=line_size)
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = addition_display_name(add, arts, art)
            add_cents = int(add.get("unit_cents") or 0) * add_qty * qty
            add_left = f"  + {add_qty}x {add_name}" if add_qty > 1 else f"  + {add_name}"
            if align_prices and add_cents:
                write_two_column(printer, add_left, _format_price(add_cents), width)
            elif add_cents:
                write_sized_line(printer, f"{add_left} {_format_price(add_cents)}", line_size)
            else:
                write_sized_line(printer, add_left, line_size)


def _write_payment_adjustments(
    printer: Dummy,
    payload: dict,
    arts: dict,
    event: dict | None,
    *,
    line_size: str = "normal",
    width: int = 48,
) -> None:
    from .discounts import order_discount_hint
    from .pricing import order_subtotal_cents, order_total_cents
    from .vouchers import voucher_definition_by_uuid

    ev = event or {}
    lines = payload.get("lines") or []
    order_discount = payload.get("order_discount")
    align = (line_size or "normal").lower() == "normal"

    subtotal = order_subtotal_cents(lines, ev, arts)
    after_order = order_total_cents(lines, order_discount, ev, arts)
    order_hint = order_discount_hint(order_discount, subtotal, after_order)
    if order_hint and subtotal > after_order:
        off = subtotal - after_order
        if align:
            write_two_column(printer, order_hint, f"-{_amount(off)}", width)
        else:
            write_sized_line(printer, f"{order_hint} -{_amount(off)}", line_size)

    for rec in payload.get("voucher_redemptions") or []:
        if not isinstance(rec, dict):
            continue
        applied = int(rec.get("applied_cents") or 0)
        if applied <= 0:
            continue
        v_uuid = str(rec.get("voucher_definition_uuid") or "").strip()
        vd = voucher_definition_by_uuid(ev, v_uuid)
        name = (vd or {}).get("name") or "Gutschein"
        label = f"Gutschein {name}"
        if align:
            write_two_column(printer, label, f"-{_amount(applied)}", width)
        else:
            write_sized_line(printer, f"{label} -{_amount(applied)}", line_size)


def _payment_receipt_due_cents(payload: dict, arts: dict, event: dict | None) -> int:
    from .pricing import order_total_cents

    ev = event or {}
    lines = payload.get("lines") or []
    order_discount = payload.get("order_discount")
    voucher_credit = int(payload.get("voucher_credit_cents") or 0)
    after_order = order_total_cents(lines, order_discount, ev, arts)
    return max(0, after_order - voucher_credit)


def build_payment_receipt_text(
    payload: dict,
    event_name: str,
    *,
    payment_id: int | None = None,
    articles: dict | None = None,
    currency: str = "EUR",
    reprint: bool = False,
    generated_at: str | None = None,
    event: dict | None = None,
    feed_lines: int = 1,
    paper_width: str | None = None,
    line_width: int | None = None,
) -> bytes:
    """Build a payment receipt ESC/POS payload (Android Bluetooth or network)."""
    arts = articles or {}
    payments = payload.get("payments") or []
    due_cents = _payment_receipt_due_cents(payload, arts, event)
    voucher_credit = int(payload.get("voucher_credit_cents") or 0)
    profile = _profile_cfg(event, "payment_receipt")
    line_size = profile.get("size_order_lines") or "normal"
    title = _event_title_for_print(event, event_name)
    width = line_width if line_width is not None else resolve_line_width(paper_width)
    logo_width = resolve_logo_max_width(width)

    def render(printer: Dummy) -> None:
        write_logo_from_event(
            printer,
            event,
            logo_enabled=bool(profile.get("logo_enabled", True)),
            max_width=logo_width,
        )
        write_sized_line(printer, "Beleg", line_size)
        if reprint:
            write_sized_line(printer, "Kopie / Nachdruck", line_size)
        if profile.get("show_event_title", True) and title:
            write_two_column(printer, title, "", width, left_bold=True)
        if payment_id is not None:
            write_sized_line(printer, f"Beleg-ID: {payment_id}", line_size)
        table = payload.get("table_number") or payload.get("settlement_table")
        if table:
            write_sized_line(printer, f"Tisch: {table}", line_size)
        coll_name = payload.get("collective_bill_name")
        if coll_name:
            write_sized_line(printer, f"Sammelrechnung: {coll_name}", line_size)
        pickup_code = payload.get("pickup_code")
        if pickup_code:
            write_sized_line(printer, f"Pickup: {pickup_code}", line_size)
        waiter_name = payload.get("waiter_name")
        if waiter_name:
            write_sized_line(printer, f"Kellner: {waiter_name}", line_size)
        order_no = payload.get("order_number")
        if order_no is not None:
            write_sized_line(printer, f"Bestellung #{order_no}", line_size)
        paid_at = payload.get("paid_at") or payload.get("settled_at") or payload.get("ordered_at") or generated_at
        if paid_at:
            write_sized_line(printer, f"Zeit: {_format_ordered_at(str(paid_at))}", line_size)
        write_separator(printer, width=width)
        _write_payment_order_lines(
            printer,
            payload,
            arts,
            event,
            currency=currency,
            line_size=line_size,
            width=width,
        )
        _write_payment_adjustments(
            printer,
            payload,
            arts,
            event,
            line_size=line_size,
            width=width,
        )
        write_separator(printer, width=width)
        if (line_size or "normal").lower() == "normal":
            write_two_column(
                printer,
                f"Total {currency}:",
                _amount(due_cents),
                width,
                left_bold=True,
            )
        else:
            write_sized_line(printer, f"Total {currency}: {_amount(due_cents)}", line_size)
        for payment in payments:
            if not isinstance(payment, dict):
                continue
            label = _payment_type_label(str(payment.get("type") or ""))
            amount = int(payment.get("amount_cents") or 0)
            if (line_size or "normal").lower() == "normal":
                write_two_column(printer, f"{label}:", _amount(amount), width)
            else:
                write_sized_line(printer, f"{label}: {_amount(amount)}", line_size)
        if voucher_credit > 0:
            if (line_size or "normal").lower() == "normal":
                write_two_column(printer, "Gutschein:", _amount(voucher_credit), width)
            else:
                write_sized_line(printer, f"Gutschein: {_amount(voucher_credit)}", line_size)
        bottom = (profile.get("bottom_line") or "").strip()
        if bottom:
            write_centered_block(printer, bottom)
        else:
            write_sized_line(printer, "Danke!", line_size)

    return render_slip(render, feed_lines=feed_lines)


def build_shift_close_receipt_text(
    session_payload: dict,
    event_name: str,
    *,
    currency: str = "EUR",
    event: dict | None = None,
    feed_lines: int = 1,
    paper_width: str | None = None,
    line_width: int | None = None,
) -> bytes:
    """Schichtabrechnung slip when closing a waiter/register shift."""
    profile = _profile_cfg(event, "payment_receipt")
    line_size = profile.get("size_order_lines") or "normal"
    title = _event_title_for_print(event, event_name)
    width = line_width if line_width is not None else resolve_line_width(paper_width)
    logo_width = resolve_logo_max_width(width)

    opening = int(session_payload.get("opening_balance_cents") or 0)
    counted = int(session_payload.get("counted_cash_cents") or 0)
    cash_earned = counted - opening
    by_method = session_payload.get("payments_by_method") or {}
    by_voucher = session_payload.get("vouchers_by_definition") or {}
    subject_name = str(session_payload.get("subject_name") or "—")
    started = session_payload.get("started_at")
    ended = session_payload.get("ended_at")

    def render(printer: Dummy) -> None:
        write_logo_from_event(
            printer,
            event,
            logo_enabled=bool(profile.get("logo_enabled", True)),
            max_width=logo_width,
        )
        write_sized_line(printer, "Schichtabrechnung", line_size)
        if profile.get("show_event_title", True) and title:
            write_two_column(printer, title, "", width, left_bold=True)
        write_separator(printer, width=width)
        write_sized_line(printer, subject_name, "large")
        if started:
            write_sized_line(printer, f"Schichtbeginn: {_format_ordered_at(str(started))}", line_size)
        if ended:
            write_sized_line(printer, f"Schichtende: {_format_ordered_at(str(ended))}", line_size)
        write_separator(printer, width=width)
        write_sized_line(printer, f"Startbetrag: {_money(opening, currency)}", line_size)
        write_sized_line(printer, f"Endbetrag: {_money(counted, currency)}", line_size)
        write_sized_line(printer, f"Bar-Einnahme: {_money(cash_earned, currency)}", line_size)
        write_separator(printer, width=width)
        for method, amount in sorted(by_method.items(), key=lambda x: x[0]):
            label = _payment_type_label(method)
            write_sized_line(printer, f"{label}: {_money(int(amount), currency)}", line_size)
        for vname, amount in sorted(by_voucher.items(), key=lambda x: x[0]):
            write_sized_line(printer, f"{vname}: {_money(int(amount), currency)}", line_size)

    return render_slip(render, feed_lines=feed_lines)


def build_voucher_slip_text(
    *,
    event_name: str,
    voucher_name: str,
    value_cents: int,
    currency: str = "EUR",
    copy_index: int | None = None,
    copy_total: int | None = None,
    generated_at: str | None = None,
    event: dict | None = None,
    feed_lines: int = 1,
) -> bytes:
    """Customer-facing amount voucher slip (one per purchased unit)."""

    def render(printer: Dummy) -> None:
        _render_receipt_slip(
            printer,
            event_name=event_name,
            event=event,
            profile_key="station_receipt",
            currency=currency,
            voucher_name=voucher_name,
            value_cents=value_cents,
            copy_index=copy_index,
            copy_total=copy_total,
            generated_at=generated_at,
        )

    return render_slip(render, feed_lines=feed_lines)


def _write_station_order_lines_formatted(
    printer: Dummy,
    payload: dict,
    arts: dict,
    width: int,
    *,
    line_size: str = "large",
    show_prices: bool = True,
    show_discount_hints: bool = True,
) -> tuple[int, int]:
    from .discounts import discount_hint
    from .pricing import line_gross_cents, line_total_cents

    total_qty = 0
    total_cents = 0
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None and not line.get("article_name"):
            continue
        qty = max(1, int(line.get("qty") or 1))
        art = arts.get(str(aid)) or arts.get(int(aid)) or {} if aid is not None else {}
        name = line.get("article_name") or art.get("name") or (f"#{aid}" if aid is not None else "—")
        if aid is not None:
            gross_cents = line_gross_cents(line, arts)
            line_cents = line_total_cents(line, arts)
            row_cents = line_cents if line.get("discount") else _line_base_total_cents(line, arts)
        else:
            from .pricing import line_unit_cents

            unit = line_unit_cents(line, arts)
            gross_cents = unit * qty
            line_cents = gross_cents
            row_cents = line_cents
        total_qty += qty
        total_cents += line_cents
        if show_prices:
            write_item_row(printer, qty, name, row_cents, width, size=line_size)
        else:
            write_sized_line(printer, f"{qty}x {name}", line_size)
        if show_discount_hints:
            hint = discount_hint(line.get("discount"), gross_cents, line_cents)
            if hint:
                write_subline(printer, hint, size=line_size)
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            add_name = addition_display_name(add, arts, art)
            sub = f"{add_qty} + {add_name}" if add_qty > 1 else f"+ {add_name}"
            write_subline(printer, sub, size=line_size)
        note = (line.get("note") or "").strip()
        if note:
            write_subline(printer, note, size=line_size)
    return total_qty, total_cents


def _render_receipt_slip(
    printer: Dummy,
    *,
    event_name: str,
    event: dict | None,
    profile_key: str,
    currency: str = "EUR",
    payload: dict | None = None,
    station_name: str | None = None,
    articles: dict | None = None,
    local_order_id: int | None = None,
    test_charset_banner: bool = False,
    voucher_name: str | None = None,
    value_cents: int | None = None,
    copy_index: int | None = None,
    copy_total: int | None = None,
    generated_at: str | None = None,
    customer_footer_fallback: str | None = None,
) -> None:
    """Unified receipt layout for station, pickup, and voucher slips."""
    arts = articles or {}
    profile = _profile_cfg(event, profile_key)
    width = _escpos_line_width()
    title = _event_title_for_print(event, event_name)
    hero_size = profile.get("size_table_or_pickup") or "xlarge"
    line_size = profile.get("size_order_lines") or "large"
    is_voucher = voucher_name is not None and value_cents is not None
    is_station_kitchen = profile_key == "station_receipt" and not is_voucher
    # Kitchen/station slips never print prices; pickup (customer_receipt) uses cloud «Preise anzeigen».
    show_prices = False if is_station_kitchen else bool(profile.get("show_price", False))

    write_logo_from_event(printer, event, logo_enabled=bool(profile.get("logo_enabled", True)))
    if test_charset_banner:
        printer.set(align="center")
        write_line(printer, "Testdruck")
        printer._raw(encode_escpos_text("Ää Öö Üü ß  Éé Èè Îî Çç\n"))
        printer.set(align="left")
    body = payload or {}

    if is_voucher:
        ts = generated_at
        if ts and "T" in str(ts):
            time_label = _format_ordered_at(str(ts))
        elif ts:
            time_label = str(ts)
        else:
            time_label = _format_ordered_at(None)
        write_two_column(printer, title, time_label, width, left_bold=True)
        ids_right = ""
        if copy_index is not None and copy_total is not None and copy_total > 1:
            ids_right = f"Kopie {copy_index}/{copy_total}"
        write_two_column(printer, "GUTSCHEIN", ids_right, width)
        write_separator(printer, width=width)
        # Between order-line "large" and full pickup/table hero (scale 8).
        write_hero(printer, voucher_name, size="xlarge", magnification=3)
        write_separator(printer, width=width)
    else:
        write_two_column(
            printer,
            title,
            _format_ordered_at(body.get("ordered_at")),
            width,
            left_bold=True,
        )
        station_label = f"Station: {station_name}" if station_name else "Station:"
        order_number = body.get("order_number")
        ids_right = _format_order_ids(
            int(order_number) if order_number is not None else None,
            local_order_id,
        )
        write_two_column(printer, station_label, ids_right, width)
        write_separator(printer, width=width)

        table = body.get("table_number")
        pickup_code = body.get("pickup_code")
        hero: str | None = None
        is_pickup_code = False
        if table is not None and int(table or 0) > 0:
            hero = str(int(table))
        elif pickup_code:
            hero = str(pickup_code)
            is_pickup_code = True
        if hero:
            if profile_key == "customer_receipt" and is_pickup_code:
                write_centered_sized(printer, "Abholcode", "normal")
            write_hero(printer, hero, size=hero_size, magnification=8)

        write_separator(printer, width=width)
        if is_station_kitchen and body.get("kitchen_partial_print"):
            write_centered_block(printer, "TEILDRUCK")
            write_separator(printer, width=width)
        total_qty, total_cents = _write_station_order_lines_formatted(
            printer,
            body,
            arts,
            width,
            line_size=line_size,
            show_prices=show_prices,
            show_discount_hints=not is_station_kitchen,
        )
        if is_station_kitchen and body.get("kitchen_excluded_lines"):
            write_separator(printer, width=width)
            write_centered_block(printer, "Noch offen")
            write_separator(printer, width=width)
            _write_station_order_lines_formatted(
                printer,
                {"lines": body.get("kitchen_excluded_lines") or []},
                arts,
                width,
                line_size=line_size,
                show_prices=False,
                show_discount_hints=False,
            )

    if not is_voucher and show_prices:
        write_separator(printer, width=width)
        total_price = f"{total_cents / 100:.2f}"
        write_two_column(printer, str(total_qty), f"{currency} {total_price}", width)

    if is_station_kitchen:
        operator = _station_operator_label(body)
        if operator:
            write_centered_small_block(printer, operator)
    elif is_voucher:
        bottom = (profile.get("bottom_line") or "").strip()
        if bottom:
            write_centered_block(printer, bottom)
        else:
            write_centered_block(printer, "Einloesung bei Zahlung.")
    elif profile_key == "customer_receipt":
        bottom = (profile.get("bottom_line") or "").strip()
        if bottom:
            write_centered_block(printer, bottom)
        elif customer_footer_fallback:
            write_centered_block(printer, customer_footer_fallback)


def _render_station_order_slip(
    printer: Dummy,
    *,
    payload: dict,
    event_name: str,
    station_name: str | None,
    articles: dict,
    event: dict | None,
    local_order_id: int | None = None,
    currency: str = "EUR",
    test_charset_banner: bool = False,
) -> None:
    """Station kitchen/order slip (uses unified layout + station_receipt profile)."""
    _render_receipt_slip(
        printer,
        payload=payload,
        event_name=event_name,
        station_name=station_name,
        articles=articles,
        event=event,
        profile_key="station_receipt",
        local_order_id=local_order_id,
        currency=currency,
        test_charset_banner=test_charset_banner,
    )


def build_escpos_receipt_text(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
    local_order_id: int | None = None,
    currency: str = "EUR",
    event: dict | None = None,
    feed_lines: int = 1,
) -> bytes:
    """Station kitchen/order slip (reference layout; honours printing profile footer/logo)."""
    arts = articles or {}

    def render(printer: Dummy) -> None:
        _render_station_order_slip(
            printer,
            payload=payload,
            event_name=event_name,
            station_name=station_name,
            articles=arts,
            event=event,
            local_order_id=local_order_id,
            currency=currency,
        )

    return render_slip(render, feed_lines=feed_lines)


def build_escpos_station_test_slip(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
    event: dict | None = None,
    feed_lines: int = 1,
) -> bytes:
    """Admin Testdruck: production station slip plus charset demo banner."""
    arts = articles or {}
    currency = (event or {}).get("currency", "EUR") if isinstance(event, dict) else "EUR"

    def render(printer: Dummy) -> None:
        _render_station_order_slip(
            printer,
            payload=payload,
            event_name=event_name,
            station_name=station_name,
            articles=arts,
            event=event,
            currency=currency,
            test_charset_banner=True,
        )

    return render_slip(render, feed_lines=feed_lines)


def build_customer_pickup_text(
    payload: dict,
    event_name: str,
    *,
    station_name: str | None = None,
    articles: dict | None = None,
    event: dict | None = None,
    local_order_id: int | None = None,
    currency: str = "EUR",
    feed_lines: int = 1,
) -> bytes:
    arts = articles or {}

    def render(printer: Dummy) -> None:
        _render_receipt_slip(
            printer,
            payload=payload,
            event_name=event_name,
            station_name=station_name,
            articles=arts,
            event=event,
            profile_key="customer_receipt",
            local_order_id=local_order_id,
            currency=currency,
            customer_footer_fallback="Bitte an der Ausgabe abholen.",
        )

    return render_slip(render, feed_lines=feed_lines)


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


async def _send_to_printer(
    host: str,
    port: int,
    data: bytes,
    *,
    db: Session | None = None,
    job_kind: str | None = None,
    station_name: str | None = None,
) -> None:
    if is_emulated_printer_mode():
        if db is None:
            db = SessionLocal()
            try:
                store_emulated_receipt(db, data=data, job_kind=job_kind, station_name=station_name)
            finally:
                db.close()
        else:
            store_emulated_receipt(db, data=data, job_kind=job_kind, station_name=station_name)
        return
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
    station_name = None
    if ev and job.station_uuid:
        station_name = station_name_from_event(ev, job.station_uuid)
    await _send_to_printer(
        job.printer_host,
        job.printer_port,
        esc,
        db=db,
        job_kind=job.job_kind,
        station_name=station_name,
    )
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
        except TimeoutError:
            pass
    log.info("Print worker stopped")


def run_print_job_sync(db: Session, job_id: int) -> None:
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        return
    order = db.query(LocalOrder).filter(LocalOrder.id == job.local_order_id).first()
    ev = _load_event_for_order(db, order) if order else None
    asyncio.run(process_print_job(db, job, ev))
