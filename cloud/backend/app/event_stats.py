"""Per-event statistics with timeframe and article timeline buckets."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from .currency import event_currency
from .edge_reporting import _distinct_order_key, _load_event_for_reporting
from .event_sales import (
    _build_name_maps,
    _resolve_attribution_bucket,
    _resolve_station_name,
    _station_bucket_key,
    payment_type_label,
)
from .models import Article, ArticleCategory, EdgeOrderItem

ARTICLE_TIMELINE_BUCKET_COUNT = 24
ALLOWED_BUCKET_COUNTS = (12, 24, 48)
TOP_ARTICLES_LIMIT = 10

ORDER_SOURCE_LABELS: dict[str, str] = {
    "waiter": "Kellner",
    "cash_register": "Kasse",
}


def parse_ordered_at(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def effective_ordered_at(row: EdgeOrderItem) -> datetime | None:
    if row.ordered_at is not None:
        dt = row.ordered_at
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    line = row.payload if isinstance(row.payload, dict) else {}
    parsed = parse_ordered_at(line.get("ordered_at"))
    if parsed is not None:
        return parsed
    if row.created_at is not None:
        dt = row.created_at
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


def resolve_sync_ordered_at(*, order_payload: dict[str, Any], line_payload: dict[str, Any]) -> datetime | None:
    header = parse_ordered_at(order_payload.get("ordered_at"))
    if header is not None:
        return header
    line = parse_ordered_at(line_payload.get("ordered_at"))
    if line is not None:
        return line
    return None


def event_article_ids(db: Session, *, event_id: int, organisation_id: int) -> set[int]:
    event = _load_event_for_reporting(db, organisation_id=organisation_id, event_id=event_id)
    if not event:
        return set()
    ids: set[int] = set()
    for station in event.stations or []:
        for article in station.articles or []:
            ids.add(int(article.id))
    return ids


def event_category_ids(db: Session, *, event_id: int, organisation_id: int) -> set[int]:
    allowed_articles = event_article_ids(db, event_id=event_id, organisation_id=organisation_id)
    if not allowed_articles:
        return set()
    rows = (
        db.query(Article.article_category_id)
        .filter(Article.id.in_(allowed_articles))
        .distinct()
        .all()
    )
    return {int(category_id) for (category_id,) in rows if category_id is not None}


def _article_category_map(db: Session, *, organisation_id: int, article_ids: set[int]) -> dict[int, int]:
    if not article_ids:
        return {}
    rows = (
        db.query(Article.id, Article.article_category_id)
        .filter(Article.id.in_(article_ids))
        .all()
    )
    return {
        int(article_id): int(category_id)
        for article_id, category_id in rows
        if article_id is not None and category_id is not None
    }


def _category_names(db: Session, *, organisation_id: int, category_ids: list[int]) -> dict[int, str]:
    if not category_ids:
        return {}
    rows = (
        db.query(ArticleCategory.id, ArticleCategory.name)
        .filter(
            ArticleCategory.organisation_id == organisation_id,
            ArticleCategory.id.in_(category_ids),
        )
        .all()
    )
    return {int(category_id): str(name) for category_id, name in rows}


def _normalize_range(from_dt: datetime, to_dt: datetime) -> tuple[datetime, datetime]:
    start = from_dt if from_dt.tzinfo else from_dt.replace(tzinfo=UTC)
    end = to_dt if to_dt.tzinfo else to_dt.replace(tzinfo=UTC)
    if start > end:
        raise ValueError("invalid_time_range")
    return start, end


def _build_time_buckets(
    from_dt: datetime,
    to_dt: datetime,
    *,
    count: int = ARTICLE_TIMELINE_BUCKET_COUNT,
) -> list[dict[str, Any]]:
    duration_seconds = (to_dt - from_dt).total_seconds()
    if duration_seconds <= 0:
        duration_seconds = 1.0
    bucket_width = duration_seconds / count
    span_hours = duration_seconds / 3600
    use_date_in_label = span_hours > 48

    buckets: list[dict[str, Any]] = []
    for i in range(count):
        start = from_dt + timedelta(seconds=bucket_width * i)
        if i == count - 1:
            end = to_dt
        else:
            end = from_dt + timedelta(seconds=bucket_width * (i + 1))
        if use_date_in_label:
            label = start.strftime("%d.%m. %H:%M")
        else:
            label = start.strftime("%H:%M")
        buckets.append(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": label,
            }
        )
    return buckets


def _bucket_index(ts: datetime, from_dt: datetime, to_dt: datetime, *, count: int) -> int | None:
    if ts < from_dt or ts > to_dt:
        return None
    duration_seconds = (to_dt - from_dt).total_seconds()
    if duration_seconds <= 0:
        return 0
    bucket_width = duration_seconds / count
    idx = int((ts - from_dt).total_seconds() / bucket_width)
    return min(idx, count - 1)


def _build_qty_timeline(
    rows: list[EdgeOrderItem],
    *,
    from_dt: datetime,
    to_dt: datetime,
    keys: list[int],
    key_names: dict[int, str],
    key_for_row: Any,
    id_field: str,
    bucket_count: int = ARTICLE_TIMELINE_BUCKET_COUNT,
) -> dict[str, Any]:
    buckets = _build_time_buckets(from_dt, to_dt, count=bucket_count)
    if not keys:
        return {
            "bucket_count": bucket_count,
            "buckets": buckets,
            "series": [],
            "totals": [],
        }

    qty_by_key: dict[int, list[int]] = {key: [0] * bucket_count for key in keys}
    total_qty: dict[int, int] = {key: 0 for key in keys}

    for row in rows:
        key = key_for_row(row)
        if key is None or int(key) not in qty_by_key:
            continue
        ts = effective_ordered_at(row)
        if ts is None:
            continue
        idx = _bucket_index(ts, from_dt, to_dt, count=bucket_count)
        if idx is None:
            continue
        qty = int(row.quantity or 0)
        qty_by_key[int(key)][idx] += qty
        total_qty[int(key)] += qty

    series = [
        {
            id_field: key,
            "name": key_names.get(key, f"{id_field} {key}"),
            "qty": qty_by_key[key],
        }
        for key in keys
    ]
    totals = [
        {
            id_field: key,
            "name": key_names.get(key, f"{id_field} {key}"),
            "qty": total_qty[key],
        }
        for key in keys
    ]
    return {
        "bucket_count": bucket_count,
        "buckets": buckets,
        "series": series,
        "totals": totals,
    }


def _build_article_timeline(
    rows: list[EdgeOrderItem],
    *,
    from_dt: datetime,
    to_dt: datetime,
    article_ids: list[int],
    article_names: dict[int, str],
    bucket_count: int = ARTICLE_TIMELINE_BUCKET_COUNT,
) -> dict[str, Any]:
    return _build_qty_timeline(
        rows,
        from_dt=from_dt,
        to_dt=to_dt,
        keys=article_ids,
        key_names=article_names,
        key_for_row=lambda row: int(row.article_id) if row.article_id is not None else None,
        id_field="article_id",
        bucket_count=bucket_count,
    )


def _build_category_timeline(
    rows: list[EdgeOrderItem],
    *,
    from_dt: datetime,
    to_dt: datetime,
    category_ids: list[int],
    category_names: dict[int, str],
    article_category_by_id: dict[int, int],
    bucket_count: int = ARTICLE_TIMELINE_BUCKET_COUNT,
) -> dict[str, Any]:
    def category_for_row(row: EdgeOrderItem) -> int | None:
        if row.article_id is None:
            return None
        return article_category_by_id.get(int(row.article_id))

    return _build_qty_timeline(
        rows,
        from_dt=from_dt,
        to_dt=to_dt,
        keys=category_ids,
        key_names=category_names,
        key_for_row=category_for_row,
        id_field="category_id",
        bucket_count=bucket_count,
    )


def _build_revenue_timeline(
    rows: list[EdgeOrderItem],
    *,
    from_dt: datetime,
    to_dt: datetime,
    bucket_count: int,
) -> dict[str, Any]:
    buckets = _build_time_buckets(from_dt, to_dt, count=bucket_count)
    line_cents = [0] * bucket_count
    for row in rows:
        ts = effective_ordered_at(row)
        if ts is None:
            continue
        idx = _bucket_index(ts, from_dt, to_dt, count=bucket_count)
        if idx is None:
            continue
        line_cents[idx] += int(row.line_total_cents or 0)
    return {
        "bucket_count": bucket_count,
        "buckets": buckets,
        "line_cents": line_cents,
    }


def _build_top_articles(
    rows: list[EdgeOrderItem],
    *,
    article_names: dict[int, str],
    limit: int = TOP_ARTICLES_LIMIT,
) -> list[dict[str, Any]]:
    totals: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row.article_id is None:
            continue
        article_id = int(row.article_id)
        if article_id not in totals:
            totals[article_id] = {
                "article_id": article_id,
                "name": article_names.get(article_id, f"Artikel {article_id}"),
                "qty": 0,
                "line_cents": 0,
            }
        totals[article_id]["qty"] += int(row.quantity or 0)
        totals[article_id]["line_cents"] += int(row.line_total_cents or 0)
    return sorted(
        totals.values(),
        key=lambda row: (row["qty"], row["line_cents"]),
        reverse=True,
    )[:limit]


def _build_by_order_source(rows: list[EdgeOrderItem]) -> list[dict[str, Any]]:
    by_source: dict[str, dict[str, Any]] = {}
    for row in rows:
        source = str(row.order_source or "waiter").lower()
        if source not in by_source:
            by_source[source] = {
                "source": source,
                "label": ORDER_SOURCE_LABELS.get(source, source),
                "qty": 0,
                "line_cents": 0,
            }
        by_source[source]["qty"] += int(row.quantity or 0)
        by_source[source]["line_cents"] += int(row.line_total_cents or 0)
    return sorted(by_source.values(), key=lambda row: row["line_cents"], reverse=True)


def build_event_stats(
    db: Session,
    *,
    organisation_id: int,
    event_id: int,
    from_dt: datetime,
    to_dt: datetime,
    article_ids: list[int] | None = None,
    category_ids: list[int] | None = None,
    bucket_count: int = ARTICLE_TIMELINE_BUCKET_COUNT,
) -> dict[str, Any]:
    if bucket_count not in ALLOWED_BUCKET_COUNTS:
        raise ValueError("invalid_bucket_count")
    start, end = _normalize_range(from_dt, to_dt)
    selected_ids = list(dict.fromkeys(article_ids or []))
    selected_category_ids = list(dict.fromkeys(category_ids or []))

    allowed = event_article_ids(db, event_id=event_id, organisation_id=organisation_id)
    invalid = [aid for aid in selected_ids if aid not in allowed]
    if invalid:
        raise ValueError("invalid_article_ids")

    allowed_categories = event_category_ids(db, event_id=event_id, organisation_id=organisation_id)
    invalid_categories = [cid for cid in selected_category_ids if cid not in allowed_categories]
    if invalid_categories:
        raise ValueError("invalid_category_ids")

    article_category_by_id = _article_category_map(db, organisation_id=organisation_id, article_ids=allowed)

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

    all_rows = (
        db.query(EdgeOrderItem)
        .filter(
            EdgeOrderItem.organisation_id == organisation_id,
            EdgeOrderItem.event_id == event_id,
        )
        .order_by(EdgeOrderItem.id.asc())
        .all()
    )

    range_rows: list[EdgeOrderItem] = []
    for row in all_rows:
        ts = effective_ordered_at(row)
        if ts is None or ts < start or ts > end:
            continue
        range_rows.append(row)

    rows: list[EdgeOrderItem] = []
    for row in range_rows:
        if selected_ids and (row.article_id is None or int(row.article_id) not in selected_ids):
            continue
        if selected_category_ids:
            category_id = (
                article_category_by_id.get(int(row.article_id))
                if row.article_id is not None
                else None
            )
            if category_id is None or category_id not in selected_category_ids:
                continue
        rows.append(row)

    article_names: dict[int, str] = {}
    for row in all_rows:
        if row.article_id is not None:
            article_names[int(row.article_id)] = str(row.article_name or f"Artikel {row.article_id}")
    for aid in selected_ids:
        article_names.setdefault(aid, f"Artikel {aid}")

    total_line = 0
    total_paid = 0
    order_keys: set[str] = set()
    by_waiter: dict[str, dict[str, Any]] = {}
    waiter_order_keys: dict[str, set[str]] = defaultdict(set)
    by_station: dict[str, dict[str, Any]] = {}
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
                "qty": 0,
                "line_cents": 0,
                "paid_cents": 0,
            }
        by_waiter[w_key]["line_cents"] += lc
        by_waiter[w_key]["paid_cents"] += lc if is_paid else 0
        by_waiter[w_key]["qty"] += int(r.quantity or 0)
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

        pm = str(r.method or "cash").lower()
        if pm not in by_payment_type:
            by_payment_type[pm] = {
                "type": pm,
                "label": payment_type_label(pm),
                "amount_cents": 0,
            }
        by_payment_type[pm]["amount_cents"] += lc if is_paid else 0

    for w_key, bucket in by_waiter.items():
        bucket["order_count"] = len(waiter_order_keys.get(w_key, set()))

    timeline_rows = rows if (selected_ids or selected_category_ids) else range_rows

    category_names = _category_names(db, organisation_id=organisation_id, category_ids=selected_category_ids)
    for cid in selected_category_ids:
        category_names.setdefault(cid, f"Kategorie {cid}")

    order_count = len(order_keys)
    average_order_value_cents = int(round(total_line / order_count)) if order_count else 0

    return {
        "currency": currency,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "bucket_count": bucket_count,
        "totals": {
            "distinct_orders_count": order_count,
            "line_cents": total_line,
            "paid_cents": total_paid,
            "open_cents": max(0, total_line - total_paid),
            "average_order_value_cents": average_order_value_cents,
        },
        "revenue_timeline": _build_revenue_timeline(
            range_rows,
            from_dt=start,
            to_dt=end,
            bucket_count=bucket_count,
        ),
        "top_articles": _build_top_articles(range_rows, article_names=article_names),
        "by_order_source": _build_by_order_source(range_rows),
        "article_timeline": _build_article_timeline(
            timeline_rows,
            from_dt=start,
            to_dt=end,
            article_ids=selected_ids,
            article_names=article_names,
            bucket_count=bucket_count,
        ),
        "category_timeline": _build_category_timeline(
            timeline_rows,
            from_dt=start,
            to_dt=end,
            category_ids=selected_category_ids,
            category_names=category_names,
            article_category_by_id=article_category_by_id,
            bucket_count=bucket_count,
        ),
        "by_payment_type": sorted(by_payment_type.values(), key=lambda x: x["amount_cents"], reverse=True),
        "by_waiter": sorted(by_waiter.values(), key=lambda x: x["line_cents"], reverse=True),
        "by_station": sorted(by_station.values(), key=lambda x: x["line_cents"], reverse=True),
    }
