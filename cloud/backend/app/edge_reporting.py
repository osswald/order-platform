"""Reporting from normalized edge mirror tables."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session, joinedload

from .currency import event_currency
from .event_sales import (
    _build_name_maps,
    _resolve_attribution_bucket,
    _resolve_station_name,
    _station_bucket_key,
    payment_type_label,
)
from .models import EdgeOrderItem, EdgePaymentBatch, EdgeSubmittedOrder, Event, EventStation


def _distinct_order_key(row: EdgeOrderItem) -> str:
    if row.submission_id is not None:
        return f"sub:{int(row.submission_id)}"
    line = row.payload if isinstance(row.payload, dict) else {}
    order_number = line.get("order_number")
    if order_number is not None and row.session_id is not None:
        return f"sess:{int(row.session_id)}:ord:{int(order_number)}"
    return f"item:{int(row.id)}"


def _audit_order_keys(db: Session, *, organisation_id: int, event_id: int) -> set[str]:
    cids = (
        db.query(EdgeSubmittedOrder.client_order_id)
        .filter(
            EdgeSubmittedOrder.organisation_id == organisation_id,
            EdgeSubmittedOrder.event_id == event_id,
        )
        .distinct()
        .all()
    )
    return {f"cid:{cid}" for (cid,) in cids if cid}


def _load_event_for_reporting(db: Session, *, organisation_id: int, event_id: int) -> Event | None:
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.cash_registers),
        )
        .filter(Event.id == event_id, Event.organisation_id == organisation_id)
        .first()
    )


def build_sales_report_v3(db: Session, *, organisation_id: int, event_id: int) -> dict[str, Any]:
    event = _load_event_for_reporting(db, organisation_id=organisation_id, event_id=event_id)
    if event:
        maps = _build_name_maps(db, event)
    else:
        maps = {
            "station_names_by_uuid": {},
            "article_station_uuid": {},
            "station_names_by_int": {},
            "waiter_by_uuid": {},
            "waiter_by_int": {},
            "waiter_by_source": {},
            "global_waiter": {},
        }
    currency = event_currency(event, "CHF")
    article_station_uuid = maps["article_station_uuid"]

    rows = (
        db.query(EdgeOrderItem)
        .filter(
            EdgeOrderItem.organisation_id == organisation_id,
            EdgeOrderItem.event_id == event_id,
        )
        .order_by(EdgeOrderItem.id.asc())
        .all()
    )
    total_line = 0
    total_paid = 0
    order_keys: set[str] = set()
    by_waiter: dict[str, dict[str, Any]] = {}
    waiter_order_keys: dict[str, set[str]] = defaultdict(set)
    by_station: dict[str, dict[str, Any]] = {}
    by_article: dict[str, dict[str, Any]] = {}
    by_payment_type: dict[str, dict[str, Any]] = {}

    for r in rows:
        order_key = _distinct_order_key(r)
        order_keys.add(order_key)
        lc = int(r.line_total_cents or 0)
        total_line += lc
        is_paid = str(r.payment_status or "").lower() == "paid"
        if is_paid:
            total_paid += lc

        w_key, waiter_name = _resolve_attribution_bucket(r, event=event, maps=maps)
        if w_key not in by_waiter:
            by_waiter[w_key] = {
                "name": waiter_name,
                "order_count": 0,
                "line_cents": 0,
                "paid_cents": 0,
            }
        by_waiter[w_key]["line_cents"] += lc
        by_waiter[w_key]["paid_cents"] += lc if is_paid else 0
        waiter_order_keys[w_key].add(order_key)

        line_payload = r.payload if isinstance(r.payload, dict) else {}
        station_uuid = str(r.station_uuid).strip() if r.station_uuid else None
        if not station_uuid and r.article_id is not None:
            station_uuid = article_station_uuid.get(int(r.article_id))
        st_key = _station_bucket_key(station_uuid, None) or "__none__"
        if st_key == "__none__" and not station_uuid:
            station_label = "Ohne Station"
        else:
            station_label = _resolve_station_name(line_payload, station_uuid, None, maps)
        if st_key not in by_station:
            by_station[st_key] = {
                "name": station_label,
                "qty": 0,
                "line_cents": 0,
            }
        by_station[st_key]["qty"] += int(r.quantity or 0)
        by_station[st_key]["line_cents"] += lc

        art_key = str(r.article_id if r.article_id is not None else r.article_name or "unknown")
        if art_key not in by_article:
            by_article[art_key] = {
                "name": str(r.article_name or "Unbekannt"),
                "qty": 0,
                "line_cents": 0,
            }
        by_article[art_key]["qty"] += int(r.quantity or 0)
        by_article[art_key]["line_cents"] += lc

        pm = str(r.method or "cash").lower()
        if pm not in by_payment_type:
            by_payment_type[pm] = {
                "type": pm,
                "label": payment_type_label(pm),
                "amount_cents": 0,
            }
        by_payment_type[pm]["amount_cents"] += lc if is_paid else 0

    if not order_keys and rows:
        order_keys = _audit_order_keys(db, organisation_id=organisation_id, event_id=event_id)

    for w_key, bucket in by_waiter.items():
        bucket["order_count"] = len(waiter_order_keys.get(w_key, set()))

    return {
        "currency": currency,
        "totals": {
            "distinct_orders_count": len(order_keys),
            "line_cents": total_line,
            "paid_cents": total_paid,
            "open_cents": max(0, total_line - total_paid),
        },
        "by_waiter": sorted(by_waiter.values(), key=lambda x: x["line_cents"], reverse=True),
        "by_station": sorted(by_station.values(), key=lambda x: x["line_cents"], reverse=True),
        "by_article": sorted(by_article.values(), key=lambda x: x["line_cents"], reverse=True),
        "by_payment_type": sorted(by_payment_type.values(), key=lambda x: x["amount_cents"], reverse=True),
    }


def build_payment_batches_report_v3(db: Session, *, organisation_id: int, event_id: int) -> dict[str, Any]:
    event = _load_event_for_reporting(db, organisation_id=organisation_id, event_id=event_id)
    currency = event_currency(event, "CHF")
    rows = (
        db.query(EdgePaymentBatch)
        .filter(
            EdgePaymentBatch.organisation_id == organisation_id,
            EdgePaymentBatch.event_id == event_id,
        )
        .order_by(EdgePaymentBatch.created_at.desc())
        .all()
    )
    return {
        "currency": currency,
        "payment_batches": [
            {
                "uuid": r.batch_uuid,
                "name": r.name,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "closed_at": r.closed_at.isoformat() if r.closed_at else None,
                "total_cents": int(r.total_cents or 0),
            }
            for r in rows
        ],
    }
