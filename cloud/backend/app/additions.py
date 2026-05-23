"""Article addition (Zusatz) link helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .models import Article, ArticleAdditionLink, ArticleCategory, Event
from .stock import snapshot_article_fields, station_linked_article_ids


def addition_delta_cents(article: Article) -> int:
    return int(round(float(article.price) * 100))


def load_links_for_bases(db: Session, base_ids: set[int]) -> dict[int, list[ArticleAdditionLink]]:
    if not base_ids:
        return {}
    rows = (
        db.query(ArticleAdditionLink)
        .filter(ArticleAdditionLink.base_article_id.in_(list(base_ids)))
        .order_by(ArticleAdditionLink.sort_order, ArticleAdditionLink.addition_article_id)
        .all()
    )
    out: dict[int, list[ArticleAdditionLink]] = {bid: [] for bid in base_ids}
    for row in rows:
        out.setdefault(row.base_article_id, []).append(row)
    return out


def addition_article_ids_for_event(db: Session, event: Event) -> set[int]:
    base_ids = station_linked_article_ids(event)
    if not base_ids:
        return set()
    rows = (
        db.query(ArticleAdditionLink.addition_article_id)
        .filter(ArticleAdditionLink.base_article_id.in_(list(base_ids)))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def event_stock_article_ids(db: Session, event: Event) -> set[int]:
    """Station/layout bundle articles plus linked Zusätze for Lagerartikel."""
    from .stock import bundle_article_ids

    ids = bundle_article_ids(event)
    ids |= addition_article_ids_for_event(db, event)
    return ids


def build_additions_for_base(
    links: list[ArticleAdditionLink],
    arts: dict[int, Article],
    stock_map: dict,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for link in links:
        add_art = arts.get(link.addition_article_id)
        if not add_art:
            continue
        fields = snapshot_article_fields(stock_map.get(link.addition_article_id))
        out.append(
            {
                "article_id": add_art.id,
                "name": add_art.name,
                "label": add_art.label,
                "price": add_art.price,
                "sort_order": link.sort_order,
                **fields,
            }
        )
    return out


def validate_base_article(db: Session, article_id: int) -> Article:
    art = (
        db.query(Article)
        .options(joinedload(Article.article_category))
        .filter(Article.id == article_id)
        .first()
    )
    if not art:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    if art.is_addition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Additions cannot be configured on a Zusatz article",
        )
    return art


def article_organisation_id(article: Article) -> int:
    return article.article_category.organisation_id


def replace_addition_links(db: Session, base: Article, items: list[dict]) -> list[ArticleAdditionLink]:
    org_id = article_organisation_id(base)
    db.query(ArticleAdditionLink).filter(ArticleAdditionLink.base_article_id == base.id).delete()

    out: list[ArticleAdditionLink] = []
    seen: set[int] = set()
    for idx, item in enumerate(items):
        add_id = int(item["addition_article_id"])
        if add_id in seen:
            continue
        seen.add(add_id)
        add_art = (
            db.query(Article)
            .join(ArticleCategory, Article.article_category_id == ArticleCategory.id)
            .filter(Article.id == add_id, ArticleCategory.organisation_id == org_id)
            .first()
        )
        if not add_art:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Addition article {add_id} not found")
        if not add_art.is_addition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Article {add_id} is not marked as Zusatz (is_addition)",
            )
        sort_order = int(item.get("sort_order") if item.get("sort_order") is not None else idx)
        row = ArticleAdditionLink(
            base_article_id=base.id,
            addition_article_id=add_id,
            sort_order=sort_order,
        )
        db.add(row)
        out.append(row)
    db.flush()
    return sorted(out, key=lambda r: (r.sort_order, r.addition_article_id))


def serialize_links_for_admin(db: Session, base: Article) -> list[dict[str, Any]]:
    links = (
        db.query(ArticleAdditionLink)
        .filter(ArticleAdditionLink.base_article_id == base.id)
        .order_by(ArticleAdditionLink.sort_order, ArticleAdditionLink.addition_article_id)
        .all()
    )
    if not links:
        return []
    add_ids = [lnk.addition_article_id for lnk in links]
    arts = {a.id: a for a in db.query(Article).filter(Article.id.in_(add_ids)).all()}
    out = []
    for lnk in links:
        a = arts.get(lnk.addition_article_id)
        if not a:
            continue
        out.append(
            {
                "addition_article_id": a.id,
                "name": a.name,
                "label": a.label,
                "price": a.price,
                "sort_order": lnk.sort_order,
            }
        )
    return out
