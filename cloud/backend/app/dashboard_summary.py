"""Organisation dashboard aggregates for the cloud admin UI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from .event_sales import build_event_sales_report
from .event_status import ALLOWED_STATUSES, PI_VISIBLE_STATUSES, normalize_status
from .models import Article, ArticleCategory, Event, Waiter
from .payment_types_config import payment_types_from_event
from .twint_qr import has_twint_qr


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def events_by_status_counts(events: list[Event]) -> dict[str, int]:
    counts = {status: 0 for status in sorted(ALLOWED_STATUSES)}
    for event in events:
        key = normalize_status(event.status)
        if key in counts:
            counts[key] += 1
    return counts


def running_event_ids(events: list[Event], now: datetime | None = None) -> list[int]:
    now = now or _utc_now()
    ids: list[int] = []
    for event in events:
        status = normalize_status(event.status)
        if status not in PI_VISIBLE_STATUSES:
            continue
        start = event.start
        end = event.end
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if start <= now <= end:
            ids.append(event.id)
    return ids


def build_attention_items(events: list[Event], now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or _utc_now()
    horizon = now + timedelta(days=7)
    items: list[dict[str, Any]] = []

    for event in events:
        status = normalize_status(event.status)
        start = event.start
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        if status == "config" and start is not None and start <= horizon:
            items.append(
                {
                    "type": "config_starting_soon",
                    "event_id": event.id,
                    "event_name": event.name,
                }
            )

        if status in PI_VISIBLE_STATUSES:
            types = payment_types_from_event(event)
            if "twint" in types and not has_twint_qr(event):
                items.append(
                    {
                        "type": "missing_twint_qr",
                        "event_id": event.id,
                        "event_name": event.name,
                    }
                )

    return items


def _lending_bucket_counts(db: Session, organisation_id: int, today) -> dict[str, int]:
    from .models import ApplianceLending

    rows = (
        db.query(ApplianceLending)
        .filter(ApplianceLending.organisation_id == organisation_id)
        .all()
    )
    current = planned = 0
    for row in rows:
        if row.returned_at is not None:
            continue
        if row.end_date < today:
            continue
        if row.start_date > today:
            planned += 1
            continue
        if row.start_date <= today <= row.end_date:
            current += 1
    return {"current": current, "planned": planned}


def _catalog_counts(db: Session, organisation_id: int) -> dict[str, int]:
    categories = (
        db.query(ArticleCategory)
        .filter(ArticleCategory.organisation_id == organisation_id)
        .count()
    )
    articles = (
        db.query(Article)
        .join(ArticleCategory)
        .filter(ArticleCategory.organisation_id == organisation_id)
        .count()
    )
    waiters = db.query(Waiter).filter(Waiter.organisation_id == organisation_id).count()
    return {"waiters": waiters, "articles": articles, "categories": categories}


def _aggregate_sales(db: Session, events: list[Event]) -> dict[str, Any]:
    prod_events = [e for e in events if normalize_status(e.status) == "prod"]
    by_event: list[dict[str, Any]] = []
    total_orders = 0
    total_line = 0
    total_paid = 0
    total_open = 0
    currency = "CHF"

    for event in prod_events:
        report = build_event_sales_report(db, event)
        totals = report["totals"]
        currency = report.get("currency") or currency
        by_event.append(
            {
                "event_id": event.id,
                "name": event.name,
                "status": normalize_status(event.status),
                "start": event.start.isoformat() if event.start else None,
                "end": event.end.isoformat() if event.end else None,
                "distinct_orders_count": totals.get("distinct_orders_count") or 0,
                "line_cents": totals.get("line_cents") or 0,
                "paid_cents": totals.get("paid_cents") or 0,
                "open_cents": totals.get("open_cents") or 0,
            }
        )
        total_orders += int(totals.get("distinct_orders_count") or 0)
        total_line += int(totals.get("line_cents") or 0)
        total_paid += int(totals.get("paid_cents") or 0)
        total_open += int(totals.get("open_cents") or 0)

    by_event.sort(key=lambda row: -(row["line_cents"] or 0))

    return {
        "currency": currency,
        "totals": {
            "distinct_orders_count": total_orders,
            "line_cents": total_line,
            "paid_cents": total_paid,
            "open_cents": total_open,
        },
        "by_event": by_event,
    }


def build_organisation_dashboard_summary(
    db: Session,
    organisation_id: int,
    organisation_name: str,
    events: list[Event],
) -> dict[str, Any]:
    now = _utc_now()
    today = now.date()
    status_counts = events_by_status_counts(events)
    running_ids = running_event_ids(events, now)

    return {
        "organisation_id": organisation_id,
        "organisation_name": organisation_name,
        "events_by_status": status_counts,
        "running_event_ids": running_ids,
        "running_events_count": len(running_ids),
        "events_total": len(events),
        "catalog": _catalog_counts(db, organisation_id),
        "lendings": _lending_bucket_counts(db, organisation_id, today),
        "attention": build_attention_items(events, now),
        "sales": _aggregate_sales(db, events),
    }
