"""Reporting from normalized edge mirror tables."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from .models import EdgeOrderItem, EdgePaymentBatch


def build_sales_report_v3(db: Session, *, organisation_id: int, event_id: int) -> dict[str, Any]:
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
    order_ids: set[int] = set()
    by_waiter: dict[str, dict[str, Any]] = defaultdict(lambda: {"name": "Unbekannt", "order_count": 0, "line_cents": 0, "paid_cents": 0})
    by_station: dict[str, dict[str, Any]] = defaultdict(lambda: {"name": "Ohne Station", "qty": 0, "line_cents": 0})
    by_article: dict[str, dict[str, Any]] = defaultdict(lambda: {"name": "Unbekannt", "qty": 0, "line_cents": 0})
    by_payment_type: dict[str, dict[str, Any]] = defaultdict(lambda: {"type": "cash", "label": "Bar", "amount_cents": 0})

    for r in rows:
        submission_id = int(r.submission_id or 0)
        if submission_id:
            order_ids.add(submission_id)
        lc = int(r.line_total_cents or 0)
        total_line += lc
        if str(r.payment_status or "").lower() == "paid":
            total_paid += lc
        waiter = str(r.waiter_uuid or "unknown")
        by_waiter[waiter]["name"] = waiter if waiter != "unknown" else "Unbekannt"
        by_waiter[waiter]["line_cents"] += lc
        by_waiter[waiter]["paid_cents"] += lc if str(r.payment_status or "").lower() == "paid" else 0
        station = str(r.station_uuid or "none")
        by_station[station]["name"] = station if station != "none" else "Ohne Station"
        by_station[station]["qty"] += int(r.quantity or 0)
        by_station[station]["line_cents"] += lc
        art = str(r.article_id or r.article_name or "unknown")
        by_article[art]["name"] = str(r.article_name or "Unbekannt")
        by_article[art]["qty"] += int(r.quantity or 0)
        by_article[art]["line_cents"] += lc
        pm = str(r.method or "cash").lower()
        by_payment_type[pm]["type"] = pm
        by_payment_type[pm]["label"] = {"cash": "Bar", "twint": "TWINT", "stripe_terminal": "Karte"}.get(pm, pm.upper())
        by_payment_type[pm]["amount_cents"] += lc if str(r.payment_status or "").lower() == "paid" else 0

    for w in by_waiter.values():
        w["order_count"] = len(order_ids)

    return {
        "currency": "CHF",
        "totals": {
            "distinct_orders_count": len(order_ids),
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
        "currency": "CHF",
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
