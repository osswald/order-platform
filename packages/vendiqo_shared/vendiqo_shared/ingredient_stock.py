"""Ingredient stock aggregation, cart usage, and order validation."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_DOWN
from typing import Any

from vendiqo_shared.stock_aggregate import aggregate_line_qty


def _dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _article_entry(articles: dict, article_id: int) -> dict | None:
    return articles.get(str(article_id)) or articles.get(article_id)


def _ingredient_entry(ingredients: dict, ingredient_id: int) -> dict | None:
    return ingredients.get(str(ingredient_id)) or ingredients.get(ingredient_id)


def _add_recipe_to_totals(
    totals: dict[int, Decimal],
    recipe: list,
    multiplier: Decimal,
) -> None:
    if multiplier <= 0 or not recipe:
        return
    for item in recipe:
        if not isinstance(item, dict):
            continue
        ing_id = item.get("ingredient_id")
        if ing_id is None:
            continue
        amount = _dec(item.get("amount") if item.get("amount") is not None else 1)
        if amount <= 0:
            continue
        totals[int(ing_id)] += multiplier * amount


def aggregate_ingredient_deductions(lines: list[dict], articles_by_id: dict[int, dict]) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for line in lines or []:
        aid = line.get("article_id")
        if aid is None:
            continue
        art = _article_entry(articles_by_id, int(aid))
        if not art:
            art = articles_by_id.get(int(aid))
        if not art:
            continue
        line_qty = _dec(line.get("qty") or 0)
        if line_qty <= 0:
            continue
        _add_recipe_to_totals(totals, art.get("ingredients") or [], line_qty)
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_id = add.get("article_id")
            if add_id is None:
                continue
            add_art = _article_entry(articles_by_id, int(add_id))
            if not add_art:
                add_art = articles_by_id.get(int(add_id))
            if not add_art:
                continue
            add_qty = _dec(max(1, int(add.get("qty") or 1)))
            _add_recipe_to_totals(totals, add_art.get("ingredients") or [], line_qty * add_qty)
    return dict(totals)


def cart_ingredient_usage(lines: list[dict], articles_by_id: dict[int, dict]) -> dict[int, Decimal]:
    return aggregate_ingredient_deductions(lines, articles_by_id)


def max_orderable_from_ingredients(
    recipe: list[dict],
    ingredient_stock: dict[int, dict],
    *,
    cart_usage: dict[int, Decimal] | None = None,
) -> dict[str, Any]:
    """Return max whole portions orderable and the limiting ingredient name."""
    cart_usage = cart_usage or {}
    max_portions: int | None = None
    limiting_name: str | None = None

    for item in recipe or []:
        if not isinstance(item, dict):
            continue
        ing_id = item.get("ingredient_id")
        if ing_id is None:
            continue
        ing_id = int(ing_id)
        ing = ingredient_stock.get(ing_id)
        if not ing or not ing.get("monitor_stock"):
            continue
        amount = _dec(item.get("amount") if item.get("amount") is not None else 1)
        if amount <= 0:
            continue
        available = _dec(ing.get("in_stock")) - _dec(cart_usage.get(ing_id))
        if available <= 0:
            name = ing.get("name") or item.get("name") or f"Zutat #{ing_id}"
            return {"max": 0, "limiting_name": name, "limiting_ingredient_id": ing_id}
        portions = int((available / amount).to_integral_value(rounding=ROUND_DOWN))
        name = ing.get("name") or item.get("name") or f"Zutat #{ing_id}"
        if max_portions is None or portions < max_portions:
            max_portions = portions
            limiting_name = name

    if max_portions is None:
        return {"max": None, "limiting_name": None, "limiting_ingredient_id": None}
    return {"max": max_portions, "limiting_name": limiting_name, "limiting_ingredient_id": None}


def _article_has_ingredients(art: dict | None) -> bool:
    return bool(art and isinstance(art.get("ingredients"), list) and art["ingredients"])


def _max_direct_article_qty(
    article_id: int,
    art: dict,
    requested: int,
    aggregated_need: dict[int, int],
) -> int:
    if not art.get("monitor_stock"):
        return requested
    available = int(art.get("in_stock") or 0)
    need = aggregated_need.get(article_id, requested)
    if need <= available:
        return requested
    return max(0, available)


def validate_order_stock(ev: dict, lines: list[dict]) -> list[dict[str, Any]]:
    """Validate full order against current bundle snapshot; return list of issues."""
    arts = ev.get("articles") or {}
    ingredients = ev.get("ingredients") or {}
    article_totals = aggregate_line_qty(lines)
    ingredient_totals = aggregate_ingredient_deductions(lines, arts)
    issues: list[dict[str, Any]] = []

    for idx, line in enumerate(lines or []):
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        aid = int(aid)
        art = _article_entry(arts, aid)
        if not art:
            continue
        requested = max(0, int(line.get("qty") or 0))
        if requested <= 0:
            continue

        if _article_has_ingredients(art):
            recipe = art.get("ingredients") or []
            ing_stock_map: dict[int, dict] = {}
            for item in recipe:
                iid = int(item["ingredient_id"])
                entry = _ingredient_entry(ingredients, iid)
                if entry:
                    ing_stock_map[iid] = entry
            max_info = max_orderable_from_ingredients(recipe, ing_stock_map, cart_usage={})
            max_qty = max_info["max"]
            if max_qty is not None and requested > max_qty:
                issues.append(
                    {
                        "line_index": idx,
                        "article_id": aid,
                        "article_name": art.get("name") or f"Artikel #{aid}",
                        "requested_qty": requested,
                        "max_orderable_qty": max_qty,
                        "reason": "ingredient",
                        "limiting_name": max_info.get("limiting_name"),
                    }
                )
            continue

        if art.get("monitor_stock"):
            available = int(art.get("in_stock") or 0)
            need = article_totals.get(aid, requested)
            if need > available:
                max_for_line = _max_direct_article_qty(aid, art, requested, article_totals)
                issues.append(
                    {
                        "line_index": idx,
                        "article_id": aid,
                        "article_name": art.get("name") or f"Artikel #{aid}",
                        "requested_qty": requested,
                        "max_orderable_qty": max_for_line,
                        "reason": "article",
                        "limiting_name": art.get("name"),
                    }
                )

    for aid, need in article_totals.items():
        art = _article_entry(arts, aid)
        if not art or _article_has_ingredients(art):
            continue
        if not art.get("monitor_stock"):
            continue
        available = int(art.get("in_stock") or 0)
        if need > available:
            if any(i.get("article_id") == aid and i.get("reason") == "article" for i in issues):
                continue
            issues.append(
                {
                    "line_index": -1,
                    "article_id": aid,
                    "article_name": art.get("name") or f"Artikel #{aid}",
                    "requested_qty": need,
                    "max_orderable_qty": available,
                    "reason": "article",
                    "limiting_name": art.get("name"),
                }
            )

    for iid, need in ingredient_totals.items():
        ing = _ingredient_entry(ingredients, iid)
        if not ing or not ing.get("monitor_stock"):
            continue
        available = _dec(ing.get("in_stock"))
        if _dec(need) > available:
            if any(i.get("reason") == "ingredient" and i.get("limiting_name") == ing.get("name") for i in issues):
                continue
            ing_name = ing.get("name") or f"Zutat #{iid}"
            issues.append(
                {
                    "line_index": -1,
                    "article_id": None,
                    "article_name": ing_name,
                    "requested_qty": float(_dec(need)),
                    "max_orderable_qty": float(available),
                    "reason": "ingredient",
                    "limiting_name": ing_name,
                }
            )
    for idx, line in enumerate(lines or []):
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        art = _article_entry(arts, int(aid))
        if not art:
            continue
        requested = max(0, int(line.get("qty") or 0))
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_id = add.get("article_id")
            if add_id is None:
                continue
            add_id = int(add_id)
            add_art = _article_entry(arts, add_id)
            if not add_art:
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            if _article_has_ingredients(add_art):
                recipe = add_art.get("ingredients") or []
                ing_stock_map: dict[int, dict] = {}
                for item in recipe:
                    iid = int(item["ingredient_id"])
                    entry = _ingredient_entry(ingredients, iid)
                    if entry:
                        ing_stock_map[iid] = entry
                effective_demand = requested * add_qty
                max_info = max_orderable_from_ingredients(recipe, ing_stock_map, cart_usage={})
                max_qty = max_info["max"]
                if max_qty is not None and effective_demand > max_qty:
                    max_lines = max_qty // add_qty if add_qty else 0
                    issues.append(
                        {
                            "line_index": idx,
                            "article_id": int(aid),
                            "article_name": art.get("name") or f"Artikel #{aid}",
                            "requested_qty": requested,
                            "max_orderable_qty": max_lines,
                            "reason": "addition_ingredient",
                            "limiting_name": max_info.get("limiting_name"),
                            "addition_name": add_art.get("name") or f"Zusatz #{add_id}",
                        }
                    )
                continue
            if not add_art.get("monitor_stock"):
                continue
            need = requested * add_qty
            available = int(add_art.get("in_stock") or 0)
            total_need = article_totals.get(add_id, 0)
            if total_need > available:
                max_add = max(0, available // add_qty) if add_qty else 0
                issues.append(
                    {
                        "line_index": idx,
                        "article_id": int(aid),
                        "article_name": art.get("name") or f"Artikel #{aid}",
                        "requested_qty": requested,
                        "max_orderable_qty": max_add,
                        "reason": "addition",
                        "limiting_name": add_art.get("name") or f"Zusatz #{add_id}",
                    }
                )

    seen: set[tuple] = set()
    deduped: list[dict[str, Any]] = []
    for issue in issues:
        key = (issue.get("line_index"), issue.get("article_id"), issue.get("reason"), issue.get("limiting_name"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped
