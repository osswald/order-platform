"""Sparse per-event article price overrides."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from .i18n.errors import api_error
from .models import Article, ArticleCategory, Event, EventArticlePrice


def load_price_map(db: Session, event_id: int, article_ids: set[int]) -> dict[int, float]:
    if not article_ids:
        return {}
    rows = (
        db.query(EventArticlePrice)
        .filter(
            EventArticlePrice.event_id == event_id,
            EventArticlePrice.article_id.in_(article_ids),
        )
        .all()
    )
    return {r.article_id: float(r.price) for r in rows}


def effective_article_price(article: Article, price_map: dict[int, float]) -> float:
    if article.id in price_map:
        return float(price_map[article.id])
    return float(article.price)


def upsert_price_overrides(
    db: Session,
    event: Event,
    items: list[dict],
) -> None:
    """Upsert or delete overrides. Each item: article_id + price (float upsert, None delete)."""
    if not items:
        return

    from .additions import event_stock_article_ids

    allowed = event_stock_article_ids(db, event)
    by_article: dict[int, float | None] = {}
    for item in items:
        aid = int(item["article_id"])
        if aid not in allowed:
            raise api_error("article_not_linked_to_event", status.HTTP_400_BAD_REQUEST, article_id=aid)
        by_article[aid] = item.get("price")

    org_id = event.organisation_id
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

    existing = {
        r.article_id: r
        for r in db.query(EventArticlePrice)
        .filter(
            EventArticlePrice.event_id == event.id,
            EventArticlePrice.article_id.in_(list(by_article.keys())),
        )
        .all()
    }
    for aid, price in by_article.items():
        row = existing.get(aid)
        if price is None:
            if row is not None:
                db.delete(row)
            continue
        value = float(price)
        if value < 0:
            raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST)
        if row is not None:
            row.price = value
        else:
            db.add(EventArticlePrice(event_id=event.id, article_id=aid, price=value))
    db.flush()


def copy_price_overrides(
    db: Session,
    *,
    source_event_id: int,
    new_event: Event,
    allowed_article_ids: set[int],
) -> None:
    if not allowed_article_ids:
        return
    source_rows = (
        db.query(EventArticlePrice)
        .filter(
            EventArticlePrice.event_id == source_event_id,
            EventArticlePrice.article_id.in_(allowed_article_ids),
        )
        .all()
    )
    for row in source_rows:
        db.add(
            EventArticlePrice(
                event_id=new_event.id,
                article_id=row.article_id,
                price=float(row.price),
            )
        )
    if source_rows:
        db.flush()
