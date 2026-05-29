"""Per-event article stock helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import Article, ArticleCategory, Event, EventArticleStock


def station_linked_article_ids(event: Event) -> set[int]:
    ids: set[int] = set()
    for st in event.stations or []:
        for a in st.articles or []:
            if not getattr(a, "is_addition", False):
                ids.add(a.id)
    return ids


def bundle_article_ids(event: Event) -> set[int]:
    """Articles in edge bundle: stations + layout cells (excludes is_addition-only picks)."""
    ids = station_linked_article_ids(event)
    for lo in event.app_layouts or []:
        for cell in lo.cells or []:
            for a in cell.articles or []:
                if not getattr(a, "is_addition", False):
                    ids.add(a.id)
    return ids


def all_bundle_article_ids(db: Session, event: Event) -> set[int]:
    """Bundle article IDs including linked Zusätze."""
    from .additions import addition_article_ids_for_event

    ids = bundle_article_ids(event)
    ids |= addition_article_ids_for_event(db, event)
    return ids


def normalize_stock_fields(monitor_stock: bool, in_stock: int | None) -> tuple[bool, int | None]:
    if not monitor_stock:
        return False, None
    if in_stock is None:
        return True, 0
    return True, max(0, int(in_stock))


def snapshot_article_fields(stock_row: EventArticleStock | None) -> dict[str, Any]:
    if stock_row is None or not stock_row.monitor_stock:
        return {"monitor_stock": False, "in_stock": None, "sellable": True}
    qty = stock_row.in_stock if stock_row.in_stock is not None else 0
    sellable = qty > 0
    return {
        "monitor_stock": True,
        "in_stock": qty,
        "sellable": sellable,
    }


def load_stock_map(db: Session, event_id: int, article_ids: set[int]) -> dict[int, EventArticleStock]:
    if not article_ids:
        return {}
    rows = (
        db.query(EventArticleStock)
        .filter(
            EventArticleStock.event_id == event_id,
            EventArticleStock.article_id.in_(article_ids),
        )
        .all()
    )
    return {r.article_id: r for r in rows}


def article_snapshot_for_event(db: Session, event: Event) -> dict[str, Any]:
    from .additions import build_additions_for_base, load_links_for_bases

    ids = all_bundle_article_ids(db, event)
    if not ids:
        return {}
    ensure_stock_rows_for_event_articles(db, event, commit=False)
    arts = {a.id: a for a in db.query(Article).filter(Article.id.in_(ids)).all()}
    stock_map = load_stock_map(db, event.id, ids)
    base_ids = bundle_article_ids(event)
    links_by_base = load_links_for_bases(db, base_ids)

    out: dict[str, Any] = {}
    for aid in ids:
        a = arts.get(aid)
        if not a:
            continue
        fields = snapshot_article_fields(stock_map.get(aid))
        entry: dict[str, Any] = {
            "id": aid,
            "name": a.name,
            "label": a.label,
            "price": a.price,
            "import_article_number": a.import_article_number,
            "description": a.description,
            "unit": a.unit,
            "income_account": a.income_account,
            "is_addition": bool(a.is_addition),
            **fields,
        }
        if not a.is_addition and aid in links_by_base:
            entry["additions"] = build_additions_for_base(links_by_base.get(aid, []), arts, stock_map)
        out[str(aid)] = entry
    return out


def _aggregate_line_qty(lines: list[dict]) -> dict[int, int]:
    totals: dict[int, int] = defaultdict(int)
    for line in lines or []:
        aid = line.get("article_id")
        if aid is None:
            continue
        line_qty = int(line.get("qty") or 0)
        if line_qty > 0:
            totals[int(aid)] += line_qty
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_id = add.get("article_id")
            if add_id is None:
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            totals[int(add_id)] += line_qty * add_qty
    return dict(totals)


def apply_stock_deductions(
    db: Session,
    event_id: int,
    lines: list[dict],
    *,
    article_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Decrement EventArticleStock for monitored articles. Returns updated snapshot entries."""
    totals = _aggregate_line_qty(lines)
    if not totals:
        return {}

    rows = (
        db.query(EventArticleStock)
        .filter(
            EventArticleStock.event_id == event_id,
            EventArticleStock.article_id.in_(list(totals.keys())),
            EventArticleStock.monitor_stock.is_(True),
        )
        .all()
    )
    by_id = {r.article_id: r for r in rows}
    updated: dict[str, Any] = {}

    for aid, need in totals.items():
        row = by_id.get(aid)
        if not row:
            continue
        available = row.in_stock if row.in_stock is not None else 0
        if need > available:
            name = (article_names or {}).get(aid) or f"Artikel #{aid}"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Nur noch {available} Stück von «{name}» verfügbar",
            )

    for aid, need in totals.items():
        row = by_id.get(aid)
        if not row:
            continue
        row.in_stock = max(0, (row.in_stock or 0) - need)
        fields = snapshot_article_fields(row)
        updated[str(aid)] = {"id": aid, **fields}

    return updated


def ensure_stock_rows_for_event_articles(
    db: Session,
    event: Event,
    *,
    commit: bool = False,
) -> list[EventArticleStock]:
    """Lazy-create EventArticleStock for station articles and linked Zusätze."""
    from .additions import addition_article_ids_for_event

    ids = station_linked_article_ids(event) | addition_article_ids_for_event(db, event)
    if not ids:
        return []
    existing = load_stock_map(db, event.id, ids)
    arts = {a.id: a for a in db.query(Article).filter(Article.id.in_(ids)).all()}
    created: list[EventArticleStock] = []
    for aid in sorted(ids):
        if aid in existing:
            continue
        art = arts.get(aid)
        monitor, in_stock = normalize_stock_fields(
            bool(art.monitor_stock) if art else False,
            art.in_stock if art else None,
        )
        row = EventArticleStock(
            event_id=event.id,
            article_id=aid,
            monitor_stock=monitor,
            in_stock=in_stock,
            baseline_in_stock=in_stock,
        )
        db.add(row)
        created.append(row)
    if created and commit:
        db.commit()
        for r in created:
            db.refresh(r)
    elif created:
        db.flush()
    all_rows = list(existing.values()) + created
    return sorted(all_rows, key=lambda r: r.article_id)


def ensure_stock_rows_for_station_articles(db: Session, event: Event, *, commit: bool = False) -> list[EventArticleStock]:
    """Backward-compatible alias."""
    return ensure_stock_rows_for_event_articles(db, event, commit=commit)


def upsert_stock_rows(
    db: Session,
    event: Event,
    items: list[dict],
) -> list[EventArticleStock]:
    from .additions import event_stock_article_ids

    allowed = event_stock_article_ids(db, event)
    if not allowed and items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stock-managed articles for this event",
        )

    org_id = event.organisation_id
    by_article: dict[int, tuple[bool, int | None]] = {}
    for item in items:
        aid = int(item["article_id"])
        if aid not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Article {aid} is not linked to this event (station or Zusatz)",
            )
        monitor, in_stock = normalize_stock_fields(
            bool(item.get("monitor_stock")),
            item.get("in_stock"),
        )
        by_article[aid] = (monitor, in_stock)

    valid_ids = {
        r[0]
        for r in db.query(Article.id)
        .join(ArticleCategory, Article.article_category_id == ArticleCategory.id)
        .filter(
            Article.id.in_(list(by_article.keys())),
            ArticleCategory.organisation_id == org_id,
        )
        .all()
    }
    for aid in by_article:
        if aid not in valid_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Article {aid} not in organisation")

    existing = load_stock_map(db, event.id, set(by_article.keys()))
    out: list[EventArticleStock] = []
    for aid, (monitor, in_stock) in by_article.items():
        row = existing.get(aid)
        if row:
            row.monitor_stock = monitor
            row.in_stock = in_stock
            row.baseline_in_stock = in_stock
        else:
            row = EventArticleStock(
                event_id=event.id,
                article_id=aid,
                monitor_stock=monitor,
                in_stock=in_stock,
                baseline_in_stock=in_stock,
            )
            db.add(row)
        out.append(row)
    db.flush()
    return sorted(out, key=lambda r: r.article_id)


def reset_event_stock_to_baseline(db: Session, event: Event) -> None:
    """Reset monitored stock to admin-configured baseline (test → prod)."""
    rows = (
        db.query(EventArticleStock)
        .filter(EventArticleStock.event_id == event.id, EventArticleStock.monitor_stock.is_(True))
        .all()
    )
    for row in rows:
        if row.baseline_in_stock is not None:
            row.in_stock = row.baseline_in_stock
    db.flush()
