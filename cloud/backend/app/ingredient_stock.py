"""Per-event ingredient stock helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session
from vendiqo_shared.ingredient_stock import aggregate_ingredient_deductions

from .i18n.errors import api_error
from .ingredients import ingredient_ids_for_event
from .models import Event, EventIngredientStock, Ingredient


def normalize_ingredient_stock_fields(
    monitor_stock: bool,
    in_stock: Decimal | float | int | None,
) -> tuple[bool, Decimal | None]:
    if not monitor_stock:
        return False, None
    if in_stock is None:
        return True, Decimal("0")
    qty = Decimal(str(in_stock))
    if qty < 0:
        qty = Decimal("0")
    return True, qty


def snapshot_ingredient_fields(stock_row: EventIngredientStock | None) -> dict[str, Any]:
    if stock_row is None or not stock_row.monitor_stock:
        return {"monitor_stock": False, "in_stock": None, "sellable": True}
    qty = stock_row.in_stock if stock_row.in_stock is not None else Decimal("0")
    sellable = qty > 0
    return {
        "monitor_stock": True,
        "in_stock": float(qty),
        "sellable": sellable,
    }


def load_ingredient_stock_map(
    db: Session,
    event_id: int,
    ingredient_ids: set[int],
) -> dict[int, EventIngredientStock]:
    if not ingredient_ids:
        return {}
    rows = (
        db.query(EventIngredientStock)
        .filter(
            EventIngredientStock.event_id == event_id,
            EventIngredientStock.ingredient_id.in_(ingredient_ids),
        )
        .all()
    )
    return {r.ingredient_id: r for r in rows}


def ensure_ingredient_stock_rows(
    db: Session,
    event: Event,
    *,
    commit: bool = False,
) -> list[EventIngredientStock]:
    ids = ingredient_ids_for_event(db, event)
    if not ids:
        return []
    existing = load_ingredient_stock_map(db, event.id, ids)
    created: list[EventIngredientStock] = []
    for iid in sorted(ids):
        if iid in existing:
            continue
        monitor, in_stock = normalize_ingredient_stock_fields(False, None)
        row = EventIngredientStock(
            event_id=event.id,
            ingredient_id=iid,
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
    return sorted(list(existing.values()) + created, key=lambda r: r.ingredient_id)


def upsert_ingredient_stock_rows(
    db: Session,
    event: Event,
    items: list[dict],
) -> list[EventIngredientStock]:
    allowed = ingredient_ids_for_event(db, event)
    org_id = event.organisation_id
    by_ingredient: dict[int, dict] = {}
    for item in items:
        iid = int(item["ingredient_id"])
        if iid not in allowed:
            raise api_error("ingredient_not_linked_to_event", status.HTTP_400_BAD_REQUEST, ingredient_id=iid)
        monitor = bool(item.get("monitor_stock"))
        entry: dict = {"monitor_stock": monitor}
        if "in_stock" in item:
            _, in_stock = normalize_ingredient_stock_fields(monitor, item.get("in_stock"))
            entry["in_stock"] = in_stock
        if "initial_in_stock" in item:
            _, initial = normalize_ingredient_stock_fields(monitor, item.get("initial_in_stock"))
            entry["initial_in_stock"] = initial
        by_ingredient[iid] = entry

    valid_ids = {
        r[0]
        for r in db.query(Ingredient.id)
        .filter(
            Ingredient.id.in_(list(by_ingredient.keys())),
            Ingredient.organisation_id == org_id,
        )
        .all()
    }
    for iid in by_ingredient:
        if iid not in valid_ids:
            raise api_error("ingredient_not_in_organisation", status.HTTP_400_BAD_REQUEST, ingredient_id=iid)

    existing = load_ingredient_stock_map(db, event.id, set(by_ingredient.keys()))
    out: list[EventIngredientStock] = []
    for iid, entry in by_ingredient.items():
        monitor = entry["monitor_stock"]
        row = existing.get(iid)
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
                _, cur = normalize_ingredient_stock_fields(monitor, None)
                init = cur
            row = EventIngredientStock(
                event_id=event.id,
                ingredient_id=iid,
                monitor_stock=monitor,
                in_stock=cur,
                baseline_in_stock=init,
            )
            db.add(row)
        out.append(row)
    db.flush()
    return sorted(out, key=lambda r: r.ingredient_id)


def ingredient_snapshot_for_event(db: Session, event: Event) -> dict[str, Any]:
    from .ingredients import organisation_ingredients_enabled

    if not organisation_ingredients_enabled(db, event.organisation_id):
        return {}
    ids = ingredient_ids_for_event(db, event)
    if not ids:
        return {}
    ensure_ingredient_stock_rows(db, event, commit=False)
    ings = {i.id: i for i in db.query(Ingredient).filter(Ingredient.id.in_(ids)).all()}
    stock_map = load_ingredient_stock_map(db, event.id, ids)
    out: dict[str, Any] = {}
    for iid in ids:
        ing = ings.get(iid)
        if not ing:
            continue
        fields = snapshot_ingredient_fields(stock_map.get(iid))
        out[str(iid)] = {
            "id": iid,
            "name": ing.name,
            "unit": ing.unit,
            **fields,
        }
    return out


def apply_ingredient_deductions(
    db: Session,
    event_id: int,
    lines: list[dict],
    articles_snapshot: dict[str, Any],
    *,
    ingredient_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    totals = aggregate_ingredient_deductions(lines, articles_snapshot)
    if not totals:
        return {}

    rows = (
        db.query(EventIngredientStock)
        .filter(
            EventIngredientStock.event_id == event_id,
            EventIngredientStock.ingredient_id.in_(list(totals.keys())),
            EventIngredientStock.monitor_stock.is_(True),
        )
        .all()
    )
    by_id = {r.ingredient_id: r for r in rows}
    updated: dict[str, Any] = {}

    for iid, need in totals.items():
        row = by_id.get(iid)
        if not row:
            continue
        available = row.in_stock if row.in_stock is not None else Decimal("0")
        if need > available:
            name = (ingredient_names or {}).get(iid) or f"Zutat #{iid}"
            raise api_error(
                "stock_insufficient",
                status.HTTP_409_CONFLICT,
                available=float(available),
                name=name,
            )

    for iid, need in totals.items():
        row = by_id.get(iid)
        if not row:
            continue
        current = row.in_stock if row.in_stock is not None else Decimal("0")
        row.in_stock = max(Decimal("0"), current - need)
        fields = snapshot_ingredient_fields(row)
        updated[str(iid)] = {"id": iid, **fields}

    return updated


def reset_event_ingredient_stock_to_baseline(db: Session, event: Event) -> None:
    rows = (
        db.query(EventIngredientStock)
        .filter(EventIngredientStock.event_id == event.id, EventIngredientStock.monitor_stock.is_(True))
        .all()
    )
    for row in rows:
        if row.baseline_in_stock is not None:
            row.in_stock = row.baseline_in_stock
    db.flush()
