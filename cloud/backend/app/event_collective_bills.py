"""Sammelrechnung list/upsert from edge-submitted order payloads."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .event_sales import (
    _build_articles_pricing_map,
    _collect_article_ids_from_orders,
    _line_for_pricing,
    distinct_order_numbers_for_rows,
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
        header.closed_at = datetime.now(timezone.utc)


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
    return {
        "id": order.id,
        "client_order_id": order.client_order_id,
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
    currency = event.currency or "EUR"

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
        orders = orders_by_uuid.get(u, [])
        order_rows = [_order_row_dict(o, arts) for o in orders]
        open_cents = sum(r["line_cents"] for r in order_rows if r["payment_status"] != "paid")
        paid_cents = sum(r["paid_cents"] for r in order_rows)
        line_cents = sum(r["line_cents"] for r in order_rows)
        has_open = any(r["payment_status"] != "paid" for r in order_rows)
        status = "open" if has_open else ("closed" if orders else "open")
        if header and header.closed_at and not has_open:
            status = "closed"
        bills.append(
            {
                "uuid": u,
                "name": header.name if header else (orders[0].payload or {}).get("collective_bill_name", "Sammelrechnung"),
                "status": status,
                "created_at": header.created_at.isoformat() if header and header.created_at else (
                    orders[0].created_at.isoformat() if orders else None
                ),
                "closed_at": header.closed_at.isoformat() if header and header.closed_at else None,
                "order_count": distinct_order_numbers_for_rows(orders),
                "line_cents": line_cents,
                "open_cents": open_cents,
                "paid_cents": paid_cents,
                "orders": order_rows,
            }
        )

    return {"currency": currency, "collective_bills": bills}
