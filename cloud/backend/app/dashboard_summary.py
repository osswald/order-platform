"""Organisation dashboard aggregates for the cloud admin UI."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .currency import organisation_country_code
from .event_status import ALLOWED_STATUSES, PI_VISIBLE_STATUSES, normalize_status
from .models import Article, ArticleCategory, EdgeOrderItem, Event, Organisation, Waiter
from .onboarding_tasks import build_onboarding_tasks, is_onboarding_dismissed
from .payment_types_config import payment_types_from_event
from .twint_qr import has_twint_qr


def _utc_now() -> datetime:
    return datetime.now(UTC)


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
            start = start.replace(tzinfo=UTC)
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
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
            start = start.replace(tzinfo=UTC)

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


def _aggregate_sales(db: Session, events: list[Event], organisation: Organisation) -> dict[str, Any]:
    """Compute per-event and aggregate sales totals using a single SQL query.

    Uses set-oriented GROUP BY on EdgeOrderItem (normalized mirrors) instead of
    calling build_event_sales_report once per production event. This avoids
    O(events × orders) full-scan behaviour on the dashboard.

    Source of truth: normalized EdgeOrderItem mirrors.  Any intentional
    discrepancy vs the legacy payload-scanner path is documented in
    tests/test_busy_event_reporting.py.
    """
    prod_events = [e for e in events if normalize_status(e.status) == "prod"]
    currency = "CHF"

    # Resolve currency from first available event
    for ev in prod_events:
        from .currency import event_currency
        currency = event_currency(ev, "CHF")
        break

    if not prod_events:
        return {
            "currency": currency,
            "country_code": organisation_country_code(organisation, "CH"),
            "totals": {
                "distinct_orders_count": 0,
                "line_cents": 0,
                "paid_cents": 0,
                "open_cents": 0,
            },
            "by_event": [],
        }

    prod_event_ids = [e.id for e in prod_events]

    # Single aggregation query across all prod events
    rows = (
        db.query(
            EdgeOrderItem.event_id,
            func.sum(EdgeOrderItem.line_total_cents).label("line_cents"),
            func.sum(
                case((EdgeOrderItem.payment_status == "paid", EdgeOrderItem.line_total_cents), else_=0)
            ).label("paid_cents"),
            # Distinct order count: use submission_id when available, fall back to row id
            func.count(
                func.distinct(
                    func.coalesce(EdgeOrderItem.submission_id, -EdgeOrderItem.id)
                )
            ).label("distinct_orders_count"),
        )
        .filter(
            EdgeOrderItem.organisation_id == organisation.id,
            EdgeOrderItem.event_id.in_(prod_event_ids),
        )
        .group_by(EdgeOrderItem.event_id)
        .all()
    )

    totals_by_event: dict[int, dict[str, Any]] = {
        row.event_id: {
            "line_cents": int(row.line_cents or 0),
            "paid_cents": int(row.paid_cents or 0),
            "distinct_orders_count": int(row.distinct_orders_count or 0),
        }
        for row in rows
    }

    by_event: list[dict[str, Any]] = []
    total_orders = 0
    total_line = 0
    total_paid = 0
    total_open = 0

    for ev in prod_events:
        t = totals_by_event.get(ev.id, {"line_cents": 0, "paid_cents": 0, "distinct_orders_count": 0})
        line = t["line_cents"]
        paid = t["paid_cents"]
        orders = t["distinct_orders_count"]
        open_cents = max(0, line - paid)

        by_event.append(
            {
                "event_id": ev.id,
                "name": ev.name,
                "status": normalize_status(ev.status),
                "start": ev.start.isoformat() if ev.start else None,
                "end": ev.end.isoformat() if ev.end else None,
                "distinct_orders_count": orders,
                "line_cents": line,
                "paid_cents": paid,
                "open_cents": open_cents,
            }
        )
        total_orders += orders
        total_line += line
        total_paid += paid
        total_open += open_cents

    by_event.sort(key=lambda row: -(row["line_cents"] or 0))

    return {
        "currency": currency,
        "country_code": organisation_country_code(organisation, "CH"),
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
    organisation: Organisation,
    events: list[Event],
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    organisation_id = organisation.id
    organisation_name = organisation.name
    now = _utc_now()
    today = now.date()
    status_counts = events_by_status_counts(events)
    running_ids = running_event_ids(events, now)
    dismissed = (
        is_onboarding_dismissed(db, user_id=user_id, organisation_id=organisation_id)
        if user_id is not None
        else False
    )

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
        "sales": _aggregate_sales(db, events, organisation),
        "onboarding": build_onboarding_tasks(
            db, organisation, events, dismissed=dismissed, user_id=user_id
        ),
    }
