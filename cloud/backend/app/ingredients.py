"""Article ingredient (Zutat) link helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session, joinedload

from .i18n.errors import api_error
from .models import Article, ArticleIngredientLink, Event, Ingredient, Organisation
from .stock import bundle_article_ids


def load_ingredient_links_for_bases(db: Session, base_ids: set[int]) -> dict[int, list[ArticleIngredientLink]]:
    if not base_ids:
        return {}
    rows = (
        db.query(ArticleIngredientLink)
        .filter(ArticleIngredientLink.base_article_id.in_(list(base_ids)))
        .order_by(ArticleIngredientLink.sort_order, ArticleIngredientLink.ingredient_id)
        .all()
    )
    out: dict[int, list[ArticleIngredientLink]] = {bid: [] for bid in base_ids}
    for row in rows:
        out.setdefault(row.base_article_id, []).append(row)
    return out


def article_ids_with_ingredients(db: Session, article_ids: set[int]) -> set[int]:
    if not article_ids:
        return set()
    rows = (
        db.query(ArticleIngredientLink.base_article_id)
        .filter(ArticleIngredientLink.base_article_id.in_(list(article_ids)))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def ingredient_ids_for_event(db: Session, event: Event) -> set[int]:
    from .additions import addition_article_ids_for_event

    article_ids = bundle_article_ids(event) | addition_article_ids_for_event(db, event)
    if not article_ids:
        return set()
    rows = (
        db.query(ArticleIngredientLink.ingredient_id)
        .filter(ArticleIngredientLink.base_article_id.in_(list(article_ids)))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def articles_without_ingredients_for_event(db: Session, event: Event) -> set[int]:
    from .additions import event_stock_article_ids

    ids = event_stock_article_ids(db, event)
    if not ids:
        return set()
    with_ing = article_ids_with_ingredients(db, ids)
    return ids - with_ing


def organisation_ingredients_enabled(db: Session, organisation_id: int) -> bool:
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    return bool(org and org.ingredients_enabled)


def ensure_ingredients_enabled(db: Session, organisation_id: int) -> None:
    if not organisation_ingredients_enabled(db, organisation_id):
        raise api_error("ingredients_not_enabled", status.HTTP_400_BAD_REQUEST)


def build_ingredients_for_base(
    links: list[ArticleIngredientLink],
    ingredients: dict[int, Ingredient],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for link in links:
        ing = ingredients.get(link.ingredient_id)
        if not ing:
            continue
        amount = link.amount if link.amount is not None else Decimal("1")
        out.append(
            {
                "ingredient_id": ing.id,
                "name": ing.name,
                "unit": ing.unit,
                "amount": float(amount),
                "sort_order": link.sort_order,
            }
        )
    return out


def validate_article_for_ingredients(db: Session, article_id: int) -> Article:
    art = (
        db.query(Article)
        .options(joinedload(Article.article_category))
        .filter(Article.id == article_id)
        .first()
    )
    if not art:
        raise api_error("article_not_found", status.HTTP_404_NOT_FOUND)
    ensure_ingredients_enabled(db, art.article_category.organisation_id)
    return art


def validate_base_article_for_ingredients(db: Session, article_id: int) -> Article:
    """Backward-compatible alias."""
    return validate_article_for_ingredients(db, article_id)


def replace_ingredient_links(db: Session, base: Article, items: list[dict]) -> list[ArticleIngredientLink]:
    org_id = base.article_category.organisation_id
    ensure_ingredients_enabled(db, org_id)
    db.query(ArticleIngredientLink).filter(ArticleIngredientLink.base_article_id == base.id).delete()

    out: list[ArticleIngredientLink] = []
    seen: set[int] = set()
    for idx, item in enumerate(items):
        ing_id = int(item["ingredient_id"])
        if ing_id in seen:
            continue
        seen.add(ing_id)
        ing = (
            db.query(Ingredient)
            .filter(Ingredient.id == ing_id, Ingredient.organisation_id == org_id)
            .first()
        )
        if not ing:
            raise api_error("ingredient_not_found", status.HTTP_400_BAD_REQUEST, ingredient_id=ing_id)
        amount = Decimal(str(item.get("amount") if item.get("amount") is not None else 1))
        if amount <= 0:
            raise api_error("ingredient_amount_invalid", status.HTTP_400_BAD_REQUEST)
        sort_order = int(item.get("sort_order") if item.get("sort_order") is not None else idx)
        row = ArticleIngredientLink(
            base_article_id=base.id,
            ingredient_id=ing_id,
            amount=amount,
            sort_order=sort_order,
        )
        db.add(row)
        out.append(row)
    db.flush()
    return sorted(out, key=lambda r: (r.sort_order, r.ingredient_id))


def serialize_ingredient_links_for_admin(db: Session, base: Article) -> list[dict[str, Any]]:
    links = (
        db.query(ArticleIngredientLink)
        .filter(ArticleIngredientLink.base_article_id == base.id)
        .order_by(ArticleIngredientLink.sort_order, ArticleIngredientLink.ingredient_id)
        .all()
    )
    if not links:
        return []
    ing_ids = [lnk.ingredient_id for lnk in links]
    ings = {i.id: i for i in db.query(Ingredient).filter(Ingredient.id.in_(ing_ids)).all()}
    out = []
    for lnk in links:
        ing = ings.get(lnk.ingredient_id)
        if not ing:
            continue
        amount = lnk.amount if lnk.amount is not None else Decimal("1")
        out.append(
            {
                "ingredient_id": ing.id,
                "name": ing.name,
                "unit": ing.unit,
                "amount": float(amount),
                "sort_order": lnk.sort_order,
            }
        )
    return out


def event_stock_article_ids_with_additions(db: Session, event: Event) -> set[int]:
    """Station/layout bundle articles plus linked Zusätze (excludes composite articles from article stock)."""
    from .additions import event_stock_article_ids

    ids = event_stock_article_ids(db, event)
    composite = article_ids_with_ingredients(db, ids)
    return ids - composite


def addition_article_ids_for_station_bases(db: Session, event: Event) -> set[int]:
    from .additions import addition_article_ids_for_event

    return addition_article_ids_for_event(db, event)
