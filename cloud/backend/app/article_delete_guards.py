"""Reference checks before deleting catalogue articles."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from .i18n import t
from .i18n.context import get_request_locale
from .i18n.errors import api_error
from .models import (
    ArticleAdditionLink,
    EdgeOrderItem,
    event_app_layout_cell_articles,
    event_station_articles,
)


def article_delete_blockers(db: Session, article_id: int) -> list[str]:
    """Return i18n keys under errors.article_delete_reason_* for active blockers."""
    reasons: list[str] = []
    if (
        db.query(ArticleAdditionLink.base_article_id)
        .filter(ArticleAdditionLink.addition_article_id == article_id)
        .first()
        is not None
    ):
        reasons.append("article_delete_reason_addition")
    if (
        db.query(event_app_layout_cell_articles.c.article_id)
        .filter(event_app_layout_cell_articles.c.article_id == article_id)
        .first()
        is not None
    ):
        reasons.append("article_delete_reason_layout")
    if (
        db.query(event_station_articles.c.article_id)
        .filter(event_station_articles.c.article_id == article_id)
        .first()
        is not None
    ):
        reasons.append("article_delete_reason_station")
    if db.query(EdgeOrderItem.id).filter(EdgeOrderItem.article_id == article_id).first() is not None:
        reasons.append("article_delete_reason_stats")
    return reasons


def assert_article_deletable(db: Session, article_id: int) -> None:
    blockers = article_delete_blockers(db, article_id)
    if not blockers:
        return
    loc = get_request_locale()
    labels = [t(f"errors.{key}", loc) for key in blockers]
    raise api_error(
        "cannot_delete_article_in_use",
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        reasons="; ".join(labels),
    )
