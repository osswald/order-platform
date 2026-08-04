"""Paginated Pi sync transactions (orders / payments) for cloud event admin."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from .currency import event_country_code, event_currency
from .event_sales import (
    _additions_signature,
    _build_articles_pricing_map,
    _build_name_maps,
    _collect_article_ids_from_orders,
    _normalize_additions,
    _resolve_waiter_name,
    format_payload_lines,
    payment_type_label,
)
from .models import EdgeSubmittedOrder, Event

logger = logging.getLogger(__name__)

# Payload conversion failures we tolerate per line; anything else is a real bug.
_LINE_PAYLOAD_ERRORS = (KeyError, TypeError, ValueError)


def _payload_dict(order: EdgeSubmittedOrder) -> dict:
    return order.payload if isinstance(order.payload, dict) else {}


def _has_order_lines(payload: dict) -> bool:
    for ln in payload.get("lines") or []:
        if isinstance(ln, dict) and ln.get("article_id") is not None:
            return True
    return False


def _transaction_kind(payload: dict) -> str:
    if str(payload.get("entity_type") or "").lower() == "cash_drawer":
        return "kassenschublade"
    if payload.get("partial_settlement"):
        return "teilzahlung"
    status = str(payload.get("payment_status") or "open").lower()
    if status == "paid" and not _has_order_lines(payload):
        return "zahlung"
    return "bestellung"


def _format_payment_methods(payments: list | None) -> str:
    parts: list[str] = []
    for p in payments or []:
        if not isinstance(p, dict):
            continue
        label = payment_type_label(str(p.get("type") or ""))
        cents = int(p.get("amount_cents") or 0)
        parts.append(f"{label} {(cents / 100):.2f}")
    return ", ".join(parts)


def _renderable_lines(raw_lines: list | None, arts: dict) -> tuple[list[dict], int, int]:
    """Format the lines that can be priced, and report the total and how many were dropped.

    Edge payloads are free-form JSON, so a line may miss `article_id` or carry values the
    pricing helpers cannot convert. Such a line contributes neither details nor value
    instead of failing the whole page.
    """
    formatted: list[dict] = []
    skipped = 0
    for line in raw_lines or []:
        try:
            entries = format_payload_lines([line], arts)
        except _LINE_PAYLOAD_ERRORS:
            entries = []
        if not entries:
            skipped += 1
            continue
        formatted.extend(entries)
    total = sum(int(entry.get("line_cents") or 0) for entry in formatted)
    return formatted, total, skipped


def _line_match_key(line: dict) -> tuple[int, str, str]:
    aid = int(line["article_id"])
    note = str(line.get("note") or "")
    adds = _normalize_additions(line.get("additions"))
    return (aid, note, _additions_signature(adds))


def _diff_line_entry(line: dict) -> tuple[tuple[int, str, str], int] | None:
    """Match key and quantity for snapshot diffing, or None when the line cannot be read."""
    try:
        return _line_match_key(line), max(1, int(line.get("qty") or 1))
    except _LINE_PAYLOAD_ERRORS:
        return None


def _transfer_note_from_destination(dest: dict) -> str:
    name = str(dest.get("to_collective_bill_name") or "").strip()
    if name:
        return f"Zu Sammelrechnung {name} verschoben"
    table = dest.get("to_table_number")
    if table is not None:
        return f"Verschoben nach Tisch {int(table)}"
    return "Verschoben"


def _moved_lines_from_payload(payload: dict, arts: dict) -> list[dict]:
    """Lines recorded on Pi when items leave this order (transfer_events in sync payload)."""
    out: list[dict] = []
    for ev in payload.get("transfer_events") or []:
        if not isinstance(ev, dict):
            continue
        note = _transfer_note_from_destination(ev)
        raw_lines = [ln for ln in (ev.get("lines") or []) if isinstance(ln, dict)]
        if not raw_lines:
            continue
        moved, _total, _skipped = _renderable_lines(raw_lines, arts)
        for entry in moved:
            out.append({**entry, "transfer_note": note, "is_moved": True})
    return out


def _infer_moved_lines_from_snapshots(
    order: EdgeSubmittedOrder,
    prior: EdgeSubmittedOrder | None,
    arts: dict,
) -> list[dict]:
    """Fallback when transfer_events missing: diff prior sync snapshot for same logical order."""
    if prior is None:
        return []
    curr_payload = _payload_dict(order)
    prev_payload = _payload_dict(prior)

    def diffable(payload: dict) -> dict[tuple[int, str, str], tuple[dict, int]]:
        out: dict[tuple[int, str, str], tuple[dict, int]] = {}
        for ln in payload.get("lines") or []:
            if not isinstance(ln, dict) or ln.get("article_id") is None:
                continue
            entry = _diff_line_entry(ln)
            if entry is None:
                continue
            key, qty = entry
            out[key] = (ln, qty)
        return out

    prev_map = diffable(prev_payload)
    curr_map = diffable(curr_payload)

    removed_raw: list[dict] = []
    for key, (prev_ln, prev_qty) in prev_map.items():
        curr = curr_map.get(key)
        curr_qty = curr[1] if curr else 0
        if curr_qty < prev_qty:
            removed_raw.append({**prev_ln, "qty": prev_qty - curr_qty})

    if not removed_raw:
        return []

    note = "Verschoben (Ziel unbekannt, ältere Sync-Daten)"
    removed, _total, _skipped = _renderable_lines(removed_raw, arts)
    return [{**entry, "transfer_note": note, "is_moved": True} for entry in removed]


def _moved_lines_for_order(
    order: EdgeSubmittedOrder,
    prior_by_order_id: dict[int, EdgeSubmittedOrder],
    arts: dict,
) -> list[dict]:
    payload = _payload_dict(order)
    moved = _moved_lines_from_payload(payload, arts)
    if moved:
        return moved
    prior = prior_by_order_id.get(order.id)
    if prior is None:
        return []
    return _infer_moved_lines_from_snapshots(order, prior, arts)


def _cash_drawer_payment_methods(payload: dict) -> str:
    register_name = str(payload.get("cash_register_name") or "").strip()
    command = str(payload.get("cash_drawer_command") or "").strip()
    payment_id = payload.get("payment_id")
    parts = ["Kassenschublade"]
    if register_name:
        parts.append(register_name)
    if command:
        parts.append(command)
    if payment_id is not None:
        parts.append(f"Beleg #{payment_id}")
    return " · ".join(parts)


def _cash_drawer_paid_cents(payload: dict) -> int:
    total = 0
    for payment in payload.get("payments") or []:
        if not isinstance(payment, dict):
            continue
        if str(payment.get("type") or "").lower() != "cash":
            continue
        total += int(payment.get("amount_cents") or 0)
    return total


def _transaction_row(
    order: EdgeSubmittedOrder,
    *,
    arts: dict,
    name_maps: dict[str, Any],
    prior_by_order_id: dict[int, EdgeSubmittedOrder],
) -> dict[str, Any]:
    payload = _payload_dict(order)
    kind = _transaction_kind(payload)
    if kind == "kassenschublade":
        register_name = str(payload.get("cash_register_name") or "").strip()
        return {
            "id": order.id,
            "created_at": payload.get("opened_at") or (order.created_at.isoformat() if order.created_at else None),
            "kind": kind,
            "client_order_id": str(payload.get("client_order_id") or order.client_order_id),
            "table_number": None,
            "collective_bill_name": None,
            "waiter_name": register_name or "—",
            "payment_status": "paid",
            "line_cents": 0,
            "moved_line_cents": 0,
            "paid_cents": _cash_drawer_paid_cents(payload),
            "payment_methods": _cash_drawer_payment_methods(payload),
            "line_count": 0,
            "lines": [],
            "moved_lines": [],
        }
    client_order_id = str(payload.get("client_order_id") or order.client_order_id)
    renderable, line_cents, skipped = _renderable_lines(payload.get("lines"), arts)
    if skipped:
        logger.warning(
            "Skipping %d unrenderable order line(s) for event %s order %s (client_order_id=%s)",
            skipped,
            order.event_id,
            order.id,
            client_order_id,
        )
    line_count = len(renderable)
    lines = renderable if kind in ("bestellung", "teilzahlung") else []

    moved_lines = _moved_lines_for_order(order, prior_by_order_id, arts)
    moved_line_cents = sum(int(m.get("line_cents") or 0) for m in moved_lines)

    waiter_uuid = payload.get("waiter_uuid")
    waiter_id_int = payload.get("waiter_id")
    if waiter_id_int is not None:
        try:
            waiter_id_int = int(waiter_id_int)
        except (TypeError, ValueError):
            waiter_id_int = None

    table_number = payload.get("table_number")
    return {
        "id": order.id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "kind": kind,
        "client_order_id": client_order_id,
        "table_number": int(table_number) if table_number is not None else None,
        "collective_bill_name": str(payload.get("collective_bill_name") or "").strip() or None,
        "waiter_name": _resolve_waiter_name(payload, waiter_uuid, waiter_id_int, name_maps),
        "payment_status": str(payload.get("payment_status") or "open"),
        "line_cents": line_cents,
        "moved_line_cents": moved_line_cents,
        "paid_cents": sum(
            int(p.get("amount_cents") or 0)
            for p in (payload.get("payments") or [])
            if isinstance(p, dict)
        ),
        "payment_methods": _format_payment_methods(payload.get("payments")),
        "line_count": line_count,
        "lines": lines,
        "moved_lines": moved_lines,
    }


def _apply_payment_status_filter(query, payment_status: str | None):
    if not payment_status:
        return query
    ps = payment_status.strip().lower()
    if ps not in ("open", "paid"):
        return query
    return query.filter(EdgeSubmittedOrder.payload["payment_status"].as_string() == ps)


def _prior_order_by_id(orders: list[EdgeSubmittedOrder]) -> dict[int, EdgeSubmittedOrder]:
    """Per sync row: previous snapshot with the same logical client_order_id."""
    by_client: dict[str, list[EdgeSubmittedOrder]] = {}
    for o in orders:
        payload = _payload_dict(o)
        key = str(payload.get("client_order_id") or o.client_order_id)
        by_client.setdefault(key, []).append(o)
    prior: dict[int, EdgeSubmittedOrder] = {}
    for group in by_client.values():
        group.sort(key=lambda x: (x.created_at or 0, x.id))
        for i in range(1, len(group)):
            prior[group[i].id] = group[i - 1]
    return prior


def _sort_rows(rows: list[dict], sort_by: str | None, sort_desc: bool) -> None:
    key = (sort_by or "created_at").strip()
    reverse = sort_desc

    def sort_key(row: dict):
        if key == "line_cents":
            return row.get("line_cents") or 0
        if key == "moved_line_cents":
            return row.get("moved_line_cents") or 0
        if key == "paid_cents":
            return row.get("paid_cents") or 0
        if key == "line_count":
            return row.get("line_count") or 0
        if key == "table_number":
            v = row.get("table_number")
            return (0 if v is None else 1, v or 0)
        if key == "kind":
            return row.get("kind") or ""
        if key == "payment_status":
            return row.get("payment_status") or ""
        if key == "waiter_name":
            return (row.get("waiter_name") or "").lower()
        if key == "collective_bill_name":
            return (row.get("collective_bill_name") or "").lower()
        if key == "client_order_id":
            return row.get("client_order_id") or ""
        return row.get("created_at") or ""

    rows.sort(key=sort_key, reverse=reverse)


def build_event_transactions_page(
    db: Session,
    event: Event,
    *,
    page: int = 1,
    items_per_page: int = 25,
    sort_by: str | None = "created_at",
    sort_desc: bool = True,
    payment_status: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    currency = event_currency(event, "EUR")
    base = db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event.id)
    base = _apply_payment_status_filter(base, payment_status)

    kind_norm = (kind or "").strip().lower() or None
    if kind_norm and kind_norm not in ("bestellung", "teilzahlung", "zahlung", "kassenschublade"):
        kind_norm = None

    sort_key = (sort_by or "created_at").strip()
    sql_sort = sort_key == "created_at"
    use_memory = bool(kind_norm) or not sql_sort

    name_maps = _build_name_maps(db, event)

    if use_memory:
        orders = base.order_by(EdgeSubmittedOrder.created_at.asc(), EdgeSubmittedOrder.id.asc()).all()
        prior_by_order_id = _prior_order_by_id(orders)
        article_ids = _collect_article_ids_from_orders(orders)
        arts = _build_articles_pricing_map(db, article_ids)
        rows = [
            _transaction_row(o, arts=arts, name_maps=name_maps, prior_by_order_id=prior_by_order_id)
            for o in orders
        ]
        if kind_norm:
            rows = [r for r in rows if r["kind"] == kind_norm]
        _sort_rows(rows, sort_key, sort_desc)
        total = len(rows)
        start = max(0, (page - 1) * items_per_page)
        items = rows[start : start + items_per_page]
    else:
        total = base.count()
        order_col = EdgeSubmittedOrder.created_at
        ordering = (order_col.desc() if sort_desc else order_col.asc(), EdgeSubmittedOrder.id.desc())
        orders = (
            base.order_by(*ordering)
            .offset(max(0, (page - 1) * items_per_page))
            .limit(items_per_page)
            .all()
        )
        # Build prior-snapshot map scoped to the current page's client_order_ids
        # to avoid loading all event orders into memory.
        page_client_ids = list({
            str(_payload_dict(o).get("client_order_id") or o.client_order_id)
            for o in orders
        })
        if page_client_ids:
            prior_candidates = (
                base.filter(EdgeSubmittedOrder.client_order_id.in_(page_client_ids))
                .order_by(EdgeSubmittedOrder.created_at.asc(), EdgeSubmittedOrder.id.asc())
                .all()
            )
        else:
            prior_candidates = []
        prior_by_order_id = _prior_order_by_id(prior_candidates)
        article_ids = _collect_article_ids_from_orders(orders)
        article_ids |= _collect_article_ids_from_orders(prior_candidates)
        arts = _build_articles_pricing_map(db, article_ids)
        items = [
            _transaction_row(o, arts=arts, name_maps=name_maps, prior_by_order_id=prior_by_order_id)
            for o in orders
        ]

    return {
        "currency": currency,
        "country_code": event_country_code(event, "CH"),
        "total": total,
        "page": page,
        "items_per_page": items_per_page,
        "items": items,
    }
