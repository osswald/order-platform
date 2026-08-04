"""Stock validation and bundle updates (mirrors cloud stock rules)."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from vendiqo_shared.ingredient_stock import aggregate_ingredient_deductions, validate_order_stock
from vendiqo_shared.stock_aggregate import aggregate_line_qty


def _article_entry(articles: dict, article_id: int) -> dict | None:
    return articles.get(str(article_id)) or articles.get(article_id)


def _ingredient_entry(ingredients: dict, ingredient_id: int) -> dict | None:
    return ingredients.get(str(ingredient_id)) or ingredients.get(ingredient_id)


def _snapshot_fields(monitor_stock: bool, in_stock: int | float | None) -> dict[str, Any]:
    if not monitor_stock:
        return {"monitor_stock": False, "in_stock": None, "sellable": True}
    qty = in_stock if in_stock is not None else 0
    return {
        "monitor_stock": True,
        "in_stock": qty,
        "sellable": float(qty) > 0 if isinstance(qty, (int, float, Decimal)) else qty > 0,
    }


def _snapshot_ingredient_fields(monitor_stock: bool, in_stock: float | Decimal | None) -> dict[str, Any]:
    if not monitor_stock:
        return {"monitor_stock": False, "in_stock": None, "sellable": True}
    qty = float(in_stock) if in_stock is not None else 0.0
    return {
        "monitor_stock": True,
        "in_stock": qty,
        "sellable": qty > 0,
    }


def _article_has_ingredients(art: dict | None) -> bool:
    return bool(art and isinstance(art.get("ingredients"), list) and art["ingredients"])


def validate_stock(ev: dict, lines: list) -> None:
    issues = validate_order_stock(ev, lines)
    if not issues:
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "stock_insufficient",
            "issues": issues,
        },
    )


def _recompute_composite_sellable(arts: dict, ingredients: dict) -> None:
    from vendiqo_shared.ingredient_stock import max_orderable_from_ingredients

    ing_stock = {}
    for key, ing in (ingredients or {}).items():
        if isinstance(ing, dict):
            ing_stock[int(key)] = ing

    for art in arts.values():
        if not isinstance(art, dict) or not _article_has_ingredients(art):
            continue
        recipe = art.get("ingredients") or []
        max_info = max_orderable_from_ingredients(recipe, ing_stock, cart_usage={})
        max_qty = max_info.get("max")
        if max_qty is not None:
            art["sellable"] = max_qty > 0


def _sync_additions_lists(arts: dict) -> None:
    for base in arts.values():
        if not isinstance(base, dict) or not base.get("additions"):
            continue
        for add in base["additions"]:
            src = _article_entry(arts, add.get("article_id"))
            if not src:
                continue
            for key in ("monitor_stock", "in_stock", "sellable"):
                if key in src:
                    add[key] = src[key]


def apply_stock_to_bundle(
    bundle: dict,
    event_id: int,
    lines: list,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Decrement monitored articles/ingredients in bundle; return updated entries."""
    ev = None
    for e in bundle.get("events", []) or []:
        if int(e.get("id")) == int(event_id):
            ev = e
            break
    if not ev:
        return {"articles": {}, "ingredients": {}}

    if strict:
        validate_stock(ev, lines)

    arts = ev.setdefault("articles", {})
    ingredients = ev.setdefault("ingredients", {})
    skip_article_ids: set[int] = set()
    for art in arts.values():
        if isinstance(art, dict) and _article_has_ingredients(art):
            aid = art.get("id")
            if aid is not None:
                skip_article_ids.add(int(aid))

    ing_totals = aggregate_ingredient_deductions(lines, arts)
    updated_ingredients: dict[str, Any] = {}
    for iid, need in ing_totals.items():
        key = str(iid)
        ing = _ingredient_entry(ingredients, iid)
        if not ing or not ing.get("monitor_stock"):
            continue
        current = ing.get("in_stock")
        if current is None:
            current = 0
        new_qty = float(current) - float(need)
        if not strict:
            new_qty = max(0.0, new_qty)
        fields = _snapshot_ingredient_fields(True, new_qty)
        merged = {**ing, **fields}
        ingredients[key] = merged
        updated_ingredients[key] = merged

    totals = aggregate_line_qty(lines)
    if skip_article_ids:
        totals = {aid: qty for aid, qty in totals.items() if aid not in skip_article_ids}

    updated_articles: dict[str, Any] = {}
    for aid, need in totals.items():
        key = str(aid)
        a = _article_entry(arts, aid)
        if not a or not a.get("monitor_stock"):
            continue
        current = a.get("in_stock")
        if current is None:
            current = 0
        new_qty = int(current) - need
        if not strict:
            new_qty = max(0, new_qty)
        fields = _snapshot_fields(True, new_qty)
        merged = {**a, **fields}
        arts[key] = merged
        updated_articles[key] = merged

    _sync_additions_lists(arts)
    _recompute_composite_sellable(arts, ingredients)
    return {"articles": updated_articles, "ingredients": updated_ingredients}


def clear_local_stock_overlay(db) -> None:
    from .models import LocalStockState

    db.query(LocalStockState).delete()


def merge_local_stock_overlay(db, bundle: dict) -> dict:
    """Apply durable local stock overrides onto a catalogue baseline (in place)."""
    from .models import LocalStockState

    rows = db.query(LocalStockState).all()
    if not rows:
        return bundle

    by_event: dict[int, dict[str, dict[int, Any]]] = {}
    for row in rows:
        bucket = by_event.setdefault(int(row.event_id), {"article": {}, "ingredient": {}})
        kind = str(row.entity_kind)
        if kind not in bucket:
            continue
        bucket[kind][int(row.entity_id)] = row

    for ev in bundle.get("events", []) or []:
        if not isinstance(ev, dict):
            continue
        eid = int(ev.get("id"))
        ov = by_event.get(eid)
        if not ov:
            continue
        arts = ev.setdefault("articles", {})
        ingredients = ev.setdefault("ingredients", {})
        for aid, row in ov["article"].items():
            key = str(aid)
            art = _article_entry(arts, aid)
            if not isinstance(art, dict):
                continue
            qty = row.in_stock
            # Articles historically use int stock; preserve int when whole.
            if isinstance(qty, float) and qty == int(qty):
                qty = int(qty)
            art.update(
                {
                    "monitor_stock": bool(row.monitor_stock),
                    "in_stock": qty,
                    "sellable": bool(row.sellable),
                }
            )
            arts[key] = art
        for iid, row in ov["ingredient"].items():
            key = str(iid)
            ing = _ingredient_entry(ingredients, iid)
            if not isinstance(ing, dict):
                continue
            ing.update(
                {
                    "monitor_stock": bool(row.monitor_stock),
                    "in_stock": float(row.in_stock),
                    "sellable": bool(row.sellable),
                }
            )
            ingredients[key] = ing
        _sync_additions_lists(arts)
        _recompute_composite_sellable(arts, ingredients)
    return bundle


def _upsert_overlay_entity(
    db,
    *,
    event_id: int,
    entity_kind: str,
    entity_id: int,
    in_stock: float | int,
    monitor_stock: bool,
    sellable: bool,
) -> None:
    from .models import LocalStockState

    row = (
        db.query(LocalStockState)
        .filter(
            LocalStockState.event_id == int(event_id),
            LocalStockState.entity_kind == entity_kind,
            LocalStockState.entity_id == int(entity_id),
        )
        .first()
    )
    if not row:
        row = LocalStockState(
            event_id=int(event_id),
            entity_kind=entity_kind,
            entity_id=int(entity_id),
        )
        db.add(row)
    row.in_stock = float(in_stock)
    row.monitor_stock = bool(monitor_stock)
    row.sellable = bool(sellable)


def persist_local_stock(
    db,
    bundle: dict,
    *,
    event_ids: set[int] | None = None,
) -> None:
    """Persist monitored stock from ``bundle`` into the overlay; update process cache.

    Does **not** rewrite ``SyncedBundle.json_body``.
    """
    from .bundle_cache import set_bundle_cache

    for ev in bundle.get("events", []) or []:
        if not isinstance(ev, dict):
            continue
        eid = int(ev.get("id"))
        if event_ids is not None and eid not in event_ids:
            continue
        arts = ev.get("articles") or {}
        ingredients = ev.get("ingredients") or {}
        for art in arts.values():
            if not isinstance(art, dict) or not art.get("monitor_stock"):
                continue
            aid = art.get("id")
            if aid is None:
                continue
            _upsert_overlay_entity(
                db,
                event_id=eid,
                entity_kind="article",
                entity_id=int(aid),
                in_stock=art.get("in_stock") if art.get("in_stock") is not None else 0,
                monitor_stock=True,
                sellable=bool(art.get("sellable")),
            )
        for ing in ingredients.values():
            if not isinstance(ing, dict) or not ing.get("monitor_stock"):
                continue
            iid = ing.get("id")
            if iid is None:
                continue
            _upsert_overlay_entity(
                db,
                event_id=eid,
                entity_kind="ingredient",
                entity_id=int(iid),
                in_stock=ing.get("in_stock") if ing.get("in_stock") is not None else 0.0,
                monitor_stock=True,
                sellable=bool(ing.get("sellable")),
            )
    set_bundle_cache(bundle)


def persist_catalogue_bundle(db, bundle: dict, *, etag: str | None = None) -> None:
    """Replace durable catalogue baseline, clear stock overlay, refresh cache."""
    import json
    from datetime import datetime

    from .bundle_cache import set_bundle_cache
    from .instant_collective_bill import ensure_instant_collective_bills_for_bundle
    from .models import SyncedBundle

    body = json.dumps(bundle)
    now = datetime.now(UTC)
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if row:
        row.json_body = body
        row.updated_at = now
        if etag is not None:
            row.etag = etag
    else:
        db.add(SyncedBundle(id=1, json_body=body, etag=etag, updated_at=now))
    clear_local_stock_overlay(db)
    ensure_instant_collective_bills_for_bundle(db, bundle)
    set_bundle_cache(bundle)


def save_bundle(db, bundle: dict) -> None:
    """Persist local stock overrides from ``bundle`` (stock path; no catalogue rewrite)."""
    persist_local_stock(db, bundle)
