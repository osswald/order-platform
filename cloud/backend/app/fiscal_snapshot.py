"""Fiscal field helpers for article bundles and order snapshots."""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .accounting_validation import resolve_article_accounting_account_id
from .models import Article, Organisation, TaxCodeRate


def effective_tax_rate_percent(
    db: Session,
    tax_code_id: int | None,
    *,
    on_date: date | None = None,
) -> float:
    if tax_code_id is None:
        return 0.0
    ref = on_date or date.today()
    row = (
        db.query(TaxCodeRate)
        .filter(
            TaxCodeRate.tax_code_id == tax_code_id,
            TaxCodeRate.valid_from <= ref,
            or_(TaxCodeRate.valid_to.is_(None), TaxCodeRate.valid_to >= ref),
        )
        .order_by(TaxCodeRate.valid_from.desc())
        .first()
    )
    return float(row.rate_percent) if row else 0.0


def fiscal_fields_for_article(
    db: Session,
    organisation: Organisation,
    article: Article,
) -> dict[str, int | float | None]:
    out: dict[str, int | float | None] = {
        "tax_code_id": None,
        "tax_rate_percent": None,
        "accounting_account_id": None,
    }
    if organisation.vat_liable and article.tax_code_id is not None:
        out["tax_code_id"] = int(article.tax_code_id)
        out["tax_rate_percent"] = effective_tax_rate_percent(db, article.tax_code_id)
    if organisation.accounts_enabled:
        category = article.article_category
        if category is not None and category.organisation is None:
            db.refresh(category)
        out["accounting_account_id"] = resolve_article_accounting_account_id(
            db,
            organisation,
            category,
            article.accounting_account_id,
        )
    return out


def load_organisation_for_event(db: Session, event) -> Organisation | None:
    org = getattr(event, "organisation", None)
    if org is not None:
        return org
    org_id = getattr(event, "organisation_id", None)
    if org_id is None:
        return None
    return (
        db.query(Organisation)
        .options(joinedload(Organisation.default_tax_code))
        .filter(Organisation.id == org_id)
        .first()
    )
