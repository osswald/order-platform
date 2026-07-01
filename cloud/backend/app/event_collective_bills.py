"""Sammelrechnung list/upsert from edge-submitted order payloads."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .currency import event_country_code, event_currency
from .event_sales import (
    _build_articles_pricing_map,
    _collect_article_ids_from_orders,
    _line_for_pricing,
    build_line_groups_from_edge_orders,
    distinct_order_numbers_for_rows,
    format_line_groups_for_api,
    format_payload_lines,
    line_total_cents,
)
from .models import EdgeSubmittedOrder, Event, EventCollectiveBill


def upsert_collective_bill_from_payload(
    db: Session,
    *,
    event_id: int,
    appliance_id: int,
    payload: dict,
) -> None:
    bill_uuid = (payload or {}).get("collective_bill_uuid")
    if not bill_uuid:
        return
    name = str((payload or {}).get("collective_bill_name") or "Sammelrechnung").strip() or "Sammelrechnung"
    row = db.query(EventCollectiveBill).filter(EventCollectiveBill.uuid == str(bill_uuid)).first()
    if not row:
        row = EventCollectiveBill(
            uuid=str(bill_uuid),
            event_id=event_id,
            name=name,
            appliance_id=appliance_id,
        )
        db.add(row)
    else:
        if name and row.name != name:
            row.name = name
        if row.event_id != event_id:
            row.event_id = event_id

    _maybe_close_collective_bill(db, row)


def _maybe_close_collective_bill(db: Session, header: EventCollectiveBill) -> None:
    """Set closed_at only when no open edge orders remain for this bill."""
    orders = (
        db.query(EdgeSubmittedOrder)
        .filter(EdgeSubmittedOrder.event_id == header.event_id)
        .all()
    )
    related = [
        o
        for o in orders
        if str((o.payload or {}).get("collective_bill_uuid") or "") == header.uuid
    ]
    if not related:
        return
    if any(str((o.payload or {}).get("payment_status") or "open").lower() != "paid" for o in related):
        return
    if header.closed_at is None:
        header.closed_at = datetime.now(UTC)


def _logical_client_order_id(order: EdgeSubmittedOrder) -> str:
    payload = order.payload if isinstance(order.payload, dict) else {}
    return str(payload.get("client_order_id") or order.client_order_id)


def _snapshot_has_lines(order: EdgeSubmittedOrder) -> bool:
    payload = order.payload if isinstance(order.payload, dict) else {}
    for ln in payload.get("lines") or []:
        if isinstance(ln, dict) and ln.get("article_id") is not None:
            return True
    return False


def _deduped_orders_for_bill(raw_orders: list[EdgeSubmittedOrder]) -> list[EdgeSubmittedOrder]:
    """Latest snapshot per payload client_order_id; prefer newest snapshot that still has lines."""
    by_key: dict[str, list[EdgeSubmittedOrder]] = defaultdict(list)
    for order in raw_orders:
        by_key[_logical_client_order_id(order)].append(order)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    out: list[EdgeSubmittedOrder] = []
    for group in by_key.values():
        sorted_g = sorted(group, key=lambda o: (o.created_at or epoch, o.id))
        best = sorted_g[-1]
        if not _snapshot_has_lines(best):
            for candidate in reversed(sorted_g):
                if _snapshot_has_lines(candidate):
                    best = candidate
                    break
        out.append(best)
    return out


def _is_open_order(order: EdgeSubmittedOrder) -> bool:
    payload = order.payload if isinstance(order.payload, dict) else {}
    return str(payload.get("payment_status") or "open").lower() != "paid"


def _order_row_dict(order: EdgeSubmittedOrder, arts: dict) -> dict:
    payload = order.payload or {}
    lines = payload.get("lines") or []
    line_cents = sum(
        line_total_cents(_line_for_pricing(ln), arts) for ln in lines if isinstance(ln, dict)
    )
    paid_cents = sum(
        int(p.get("amount_cents") or 0)
        for p in (payload.get("payments") or [])
        if isinstance(p, dict)
    )
    if paid_cents == 0 and str(payload.get("payment_status") or "open").lower() == "paid":
        paid_cents = line_cents
    logical_cid = payload.get("client_order_id") or order.client_order_id
    return {
        "id": order.id,
        "client_order_id": logical_cid,
        "order_number": payload.get("order_number"),
        "ordered_at": payload.get("ordered_at"),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "payment_status": payload.get("payment_status") or "open",
        "line_cents": line_cents,
        "paid_cents": paid_cents,
        "lines": format_payload_lines(lines, arts),
        "payments": payload.get("payments") or [],
    }


def build_event_collective_bills_list(db: Session, event: Event) -> dict:
    currency = event_currency(event, "EUR")

    headers = {
        r.uuid: r
        for r in db.query(EventCollectiveBill).filter(EventCollectiveBill.event_id == event.id).all()
    }
    orders_by_uuid: dict[str, list[EdgeSubmittedOrder]] = defaultdict(list)
    all_event_orders = (
        db.query(EdgeSubmittedOrder)
        .filter(EdgeSubmittedOrder.event_id == event.id)
        .order_by(EdgeSubmittedOrder.created_at.asc())
        .all()
    )
    collective_orders = [o for o in all_event_orders if (o.payload or {}).get("collective_bill_uuid")]
    article_ids = _collect_article_ids_from_orders(collective_orders)
    arts = _build_articles_pricing_map(db, article_ids)

    for order in all_event_orders:
        payload = order.payload or {}
        u = payload.get("collective_bill_uuid")
        if u:
            orders_by_uuid[str(u)].append(order)

    all_uuids = set(headers.keys()) | set(orders_by_uuid.keys())
    bills = []
    for u in sorted(all_uuids, key=lambda x: (headers.get(x).created_at if headers.get(x) else None, x)):
        header = headers.get(u)
        raw_orders = orders_by_uuid.get(u, [])
        display_orders = _deduped_orders_for_bill(raw_orders)
        open_orders = [o for o in display_orders if _is_open_order(o)]
        line_groups_raw = build_line_groups_from_edge_orders(display_orders, arts)
        open_groups_raw = build_line_groups_from_edge_orders(open_orders, arts)
        line_groups = format_line_groups_for_api(line_groups_raw, arts)
        line_cents = sum(g["line_total_cents"] for g in line_groups_raw)
        open_cents = sum(g["line_total_cents"] for g in open_groups_raw)
        paid_cents = sum(
            sum(
                int(p.get("amount_cents") or 0)
                for p in ((o.payload or {}).get("payments") or [])
                if isinstance(p, dict)
            )
            for o in display_orders
        )
        has_open = bool(open_orders)
        if paid_cents == 0 and display_orders and not has_open:
            paid_cents = line_cents
        order_rows = [_order_row_dict(o, arts) for o in display_orders]
        status = "open" if has_open else ("closed" if display_orders else "open")
        if header and header.closed_at and not has_open:
            status = "closed"
        bills.append(
            {
                "uuid": u,
                "name": (
                    header.name
                    if header
                    else ((display_orders[0].payload or {}).get("collective_bill_name", "Sammelrechnung") if display_orders else "Sammelrechnung")
                ),
                "status": status,
                "created_at": header.created_at.isoformat() if header and header.created_at else (
                    display_orders[0].created_at.isoformat() if display_orders else None
                ),
                "closed_at": header.closed_at.isoformat() if header and header.closed_at else None,
                "order_count": distinct_order_numbers_for_rows(display_orders),
                "line_cents": line_cents,
                "open_cents": open_cents,
                "paid_cents": paid_cents,
                "line_groups": line_groups,
                "orders": order_rows,
            }
        )

    return {"currency": currency, "country_code": event_country_code(event, "CH"), "collective_bills": bills}


def build_single_collective_bill(db: Session, event: Event, bill_uuid: str) -> dict | None:
    """Return one collective bill dict from build_event_collective_bills_list, or None."""
    result = build_event_collective_bills_list(db, event)
    target = str(bill_uuid)
    for bill in result.get("collective_bills") or []:
        if str(bill.get("uuid") or "") == target:
            return {**bill, "_currency": result.get("currency")}
    return None
