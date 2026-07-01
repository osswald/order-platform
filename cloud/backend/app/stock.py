"""Per-event article stock helpers."""

from __future__ import annotations

from typing import Any

from fastapi import status
from sqlalchemy.orm import Session, joinedload
from vendiqo_shared.stock_aggregate import aggregate_line_qty

from .i18n.errors import api_error
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
    from .fiscal_snapshot import fiscal_fields_for_article, load_organisation_for_event
    from .ingredient_stock import ingredient_snapshot_for_event
    from .ingredients import (
        build_ingredients_for_base,
        load_ingredient_links_for_bases,
        organisation_ingredients_enabled,
    )
    from .models import Ingredient

    ids = all_bundle_article_ids(db, event)
    if not ids:
        return {}
    organisation = load_organisation_for_event(db, event)
    ingredients_on = organisation_ingredients_enabled(db, event.organisation_id)
    ensure_stock_rows_for_event_articles(db, event, commit=False)
    arts = {
        a.id: a
        for a in (
            db.query(Article)
            .options(joinedload(Article.article_category))
            .filter(Article.id.in_(ids))
            .all()
        )
    }
    stock_map = load_stock_map(db, event.id, ids)
    base_ids = bundle_article_ids(event)
    links_by_base = load_links_for_bases(db, base_ids)
    ingredient_links_by_base = load_ingredient_links_for_bases(db, ids) if ingredients_on else {}
    all_ingredient_ids: set[int] = set()
    for links in ingredient_links_by_base.values():
        for link in links:
            all_ingredient_ids.add(link.ingredient_id)
    ingredients_map = (
        {i.id: i for i in db.query(Ingredient).filter(Ingredient.id.in_(all_ingredient_ids)).all()}
        if all_ingredient_ids
        else {}
    )

    out: dict[str, Any] = {}
    for aid in ids:
        a = arts.get(aid)
        if not a:
            continue
        has_recipe = bool(ingredient_links_by_base.get(aid))
        if has_recipe and ingredients_on:
            fields = {"monitor_stock": False, "in_stock": None, "sellable": True}
        else:
            fields = snapshot_article_fields(stock_map.get(aid))
        entry: dict[str, Any] = {
            "id": aid,
            "name": a.name,
            "label": a.label,
            "price": a.price,
            "import_article_number": a.import_article_number,
            "description": a.description,
            "unit": a.unit,
            "is_addition": bool(a.is_addition),
            **fields,
        }
        if not a.is_addition and aid in links_by_base:
            entry["additions"] = build_additions_for_base(links_by_base.get(aid, []), arts, stock_map)
        if ingredients_on and aid in ingredient_links_by_base:
            recipe = build_ingredients_for_base(ingredient_links_by_base.get(aid, []), ingredients_map)
            entry["ingredients"] = recipe
            if recipe:
                from vendiqo_shared.ingredient_stock import max_orderable_from_ingredients

                ing_snap = ingredient_snapshot_for_event(db, event)
                ing_stock = {int(k): v for k, v in ing_snap.items()}
                max_info = max_orderable_from_ingredients(recipe, ing_stock, cart_usage={})
                max_qty = max_info.get("max")
                if max_qty is not None:
                    entry["sellable"] = max_qty > 0
        if organisation is not None:
            entry.update(fiscal_fields_for_article(db, organisation, a))
        out[str(aid)] = entry

    for entry in out.values():
        adds = entry.get("additions")
        if not adds:
            continue
        enriched: list[dict[str, Any]] = []
        for add in adds:
            full = out.get(str(add.get("article_id")))
            if full:
                add = {
                    **add,
                    "monitor_stock": full.get("monitor_stock"),
                    "in_stock": full.get("in_stock"),
                    "sellable": full.get("sellable"),
                }
                if full.get("ingredients"):
                    add["ingredients"] = full["ingredients"]
            enriched.append(add)
        entry["additions"] = enriched

    return out


def apply_stock_deductions(
    db: Session,
    event_id: int,
    lines: list[dict],
    *,
    article_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Decrement EventArticleStock and ingredient stock. Returns updated article snapshot entries."""
    from .ingredient_stock import apply_ingredient_deductions, ingredient_snapshot_for_event
    from .ingredients import article_ids_with_ingredients, organisation_ingredients_enabled

    event = db.query(Event).filter(Event.id == event_id).first()
    articles_snapshot = article_snapshot_for_event(db, event) if event else {}
    skip_article_ids: set[int] = set()
    if event and organisation_ingredients_enabled(db, event.organisation_id):
        skip_article_ids = article_ids_with_ingredients(db, all_bundle_article_ids(db, event))
        from .ingredient_stock import ingredient_snapshot_for_event

        ing_snap = ingredient_snapshot_for_event(db, event)
        ing_names = {int(k): v.get("name", f"Zutat #{k}") for k, v in ing_snap.items()}
        apply_ingredient_deductions(
            db,
            event_id,
            lines,
            articles_snapshot,
            ingredient_names=ing_names,
        )

    totals = aggregate_line_qty(lines)
    if skip_article_ids:
        totals = {aid: qty for aid, qty in totals.items() if aid not in skip_article_ids}

    updated: dict[str, Any] = {}
    if not totals:
        return updated

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

    for aid, need in totals.items():
        row = by_id.get(aid)
        if not row:
            continue
        available = row.in_stock if row.in_stock is not None else 0
        if need > available:
            name = (article_names or {}).get(aid) or f"Artikel #{aid}"
            raise api_error("stock_insufficient", status.HTTP_409_CONFLICT, available=available, name=name)

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
    """Lazy-create EventArticleStock for station articles and linked Zusätze (excludes composite articles)."""
    from .additions import event_stock_article_ids
    from .ingredients import article_ids_with_ingredients, organisation_ingredients_enabled

    all_ids = event_stock_article_ids(db, event)
    composite: set[int] = set()
    if organisation_ingredients_enabled(db, event.organisation_id):
        composite = article_ids_with_ingredients(db, all_ids)
    ids = all_ids - composite
    if not ids:
        return []
    existing = load_stock_map(db, event.id, ids)
    created: list[EventArticleStock] = []
    for aid in sorted(ids):
        if aid in existing:
            continue
        monitor, in_stock = normalize_stock_fields(False, None)
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
    from .ingredients import article_ids_with_ingredients, organisation_ingredients_enabled

    allowed = event_stock_article_ids(db, event)
    if organisation_ingredients_enabled(db, event.organisation_id):
        composite = article_ids_with_ingredients(db, allowed)
        allowed -= composite
    if not allowed and items:
        raise api_error("no_stock_managed_articles", status.HTTP_400_BAD_REQUEST)

    org_id = event.organisation_id
    by_article: dict[int, dict] = {}
    for item in items:
        aid = int(item["article_id"])
        if aid not in allowed:
            raise api_error("article_not_linked_to_event", status.HTTP_400_BAD_REQUEST, article_id=aid)
        monitor = bool(item.get("monitor_stock"))
        entry: dict = {"monitor_stock": monitor}
        if "in_stock" in item:
            _, in_stock = normalize_stock_fields(monitor, item.get("in_stock"))
            entry["in_stock"] = in_stock
        if "initial_in_stock" in item:
            _, initial = normalize_stock_fields(monitor, item.get("initial_in_stock"))
            entry["initial_in_stock"] = initial
        by_article[aid] = entry

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
            raise api_error("article_not_in_organisation", status.HTTP_400_BAD_REQUEST, article_id=aid)

    existing = load_stock_map(db, event.id, set(by_article.keys()))
    out: list[EventArticleStock] = []
    for aid, entry in by_article.items():
        monitor = entry["monitor_stock"]
        row = existing.get(aid)
        if row:
            row.monitor_stock = monitor
            if "in_stock" in entry:
                row.in_stock = entry["in_stock"]
            if "initial_in_stock" in entry:
                row.baseline_in_stock = entry["initial_in_stock"]
        else:
            cur = entry.get("in_stock")
            init = entry.get("initial_in_stock")
            if cur is None and init is not None:
                cur = init
            if init is None and cur is not None:
                init = cur
            if cur is None and init is None:
                _, cur = normalize_stock_fields(monitor, None)
                init = cur
            row = EventArticleStock(
                event_id=event.id,
                article_id=aid,
                monitor_stock=monitor,
                in_stock=cur,
                baseline_in_stock=init,
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
