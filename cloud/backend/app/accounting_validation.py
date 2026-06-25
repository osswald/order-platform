"""Validation helpers for organisation accounting accounts."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from .i18n.errors import api_error
from .models import AccountingAccount, Article, ArticleCategory, Organisation


def ensure_accounting_account_for_org(
    db: Session, accounting_account_id: int | None, organisation_id: int
) -> AccountingAccount | None:
    if accounting_account_id is None:
        return None
    account = (
        db.query(AccountingAccount)
        .filter(
            AccountingAccount.id == accounting_account_id,
            AccountingAccount.organisation_id == organisation_id,
        )
        .first()
    )
    if not account:
        raise api_error("accounting_account_not_found", status.HTTP_400_BAD_REQUEST)
    return account


def validate_category_accounting_account(
    db: Session, organisation: Organisation, accounting_account_id: int | None
) -> int | None:
    if not organisation.accounts_enabled:
        return None
    ensure_accounting_account_for_org(db, accounting_account_id, organisation.id)
    return accounting_account_id


def validate_article_accounting_account(
    db: Session, organisation: Organisation, accounting_account_id: int | None
) -> int | None:
    if not organisation.accounts_enabled:
        return None
    ensure_accounting_account_for_org(db, accounting_account_id, organisation.id)
    return accounting_account_id


def default_accounting_account_for_category(
    db: Session, category: ArticleCategory
) -> int | None:
    if category.accounting_account_id is not None:
        return category.accounting_account_id
    org = category.organisation
    if org is None or not org.accounts_enabled:
        return None
    default = (
        db.query(AccountingAccount)
        .filter(
            AccountingAccount.organisation_id == org.id,
            AccountingAccount.is_default_for_article_categories.is_(True),
        )
        .first()
    )
    return default.id if default else None


def resolve_article_accounting_account_id(
    db: Session,
    organisation: Organisation,
    category: ArticleCategory,
    accounting_account_id: int | None,
) -> int | None:
    if not organisation.accounts_enabled:
        return None
    if accounting_account_id is not None:
        validate_article_accounting_account(db, organisation, accounting_account_id)
        return accounting_account_id
    return default_accounting_account_for_category(db, category)


def clear_org_category_default_flag(db: Session, organisation_id: int, except_id: int | None = None) -> None:
    query = db.query(AccountingAccount).filter(
        AccountingAccount.organisation_id == organisation_id,
        AccountingAccount.is_default_for_article_categories.is_(True),
    )
    if except_id is not None:
        query = query.filter(AccountingAccount.id != except_id)
    for account in query.all():
        account.is_default_for_article_categories = False


def assert_accounting_account_deletable(db: Session, account_id: int) -> None:
    if (
        db.query(Article.id).filter(Article.accounting_account_id == account_id).first()
        is not None
    ):
        raise api_error("accounting_account_in_use", status.HTTP_400_BAD_REQUEST)
    if (
        db.query(ArticleCategory.id)
        .filter(ArticleCategory.accounting_account_id == account_id)
        .first()
        is not None
    ):
        raise api_error("accounting_account_in_use", status.HTTP_400_BAD_REQUEST)
