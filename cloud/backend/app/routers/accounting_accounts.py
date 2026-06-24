from typing import List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..accounting_validation import (
    assert_accounting_account_deletable,
    clear_org_category_default_flag,
    ensure_accounting_account_for_org,
)
from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import (
    AccountingAccount,
    AccountingAccountPaymentTypeDefault,
    AccountingAccountTaxCodeDefault,
    PaymentType,
    TaxCode,
    User,
)
from ..payment_type_reference import get_payment_type_or_404
from ..tax_code_validation import ensure_tax_code_for_country
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_user_can_use_organisation,
    get_current_tenant,
)

router = APIRouter()


def _raise_duplicate_account_number() -> None:
    raise api_error("accounting_account_number_exists", status.HTTP_400_BAD_REQUEST)


class AccountingAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_id: int
    name: str
    number: str
    is_default_for_article_categories: bool
    default_payment_type_ids: List[int] = []


class AccountingAccountCreate(BaseModel):
    organisation_id: int
    name: str = Field(..., min_length=1)
    number: str = Field(..., min_length=1)
    is_default_for_article_categories: bool = False


class AccountingAccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    number: str | None = Field(None, min_length=1)
    is_default_for_article_categories: bool | None = None


class PaymentTypeAccountDefaultItem(BaseModel):
    payment_type_id: int
    accounting_account_id: int | None = None


class PaymentTypeAccountDefaultsUpdate(BaseModel):
    defaults: List[PaymentTypeAccountDefaultItem] = Field(default_factory=list)


class PaymentTypeAccountDefaultRead(BaseModel):
    payment_type_id: int
    payment_type_slug: str
    accounting_account_id: int | None = None


class TaxCodeAccountDefaultItem(BaseModel):
    tax_code_id: int
    accounting_account_id: int | None = None


class TaxCodeAccountDefaultsUpdate(BaseModel):
    defaults: List[TaxCodeAccountDefaultItem] = Field(default_factory=list)


class TaxCodeAccountDefaultRead(BaseModel):
    tax_code_id: int
    tax_code_name: str
    accounting_account_id: int | None = None


def _default_payment_type_ids(db: Session, account_id: int) -> list[int]:
    rows = (
        db.query(AccountingAccountPaymentTypeDefault.payment_type_id)
        .filter(AccountingAccountPaymentTypeDefault.accounting_account_id == account_id)
        .all()
    )
    return [row[0] for row in rows]


def _account_response(db: Session, account: AccountingAccount) -> dict:
    return {
        "id": account.id,
        "organisation_id": account.organisation_id,
        "name": account.name,
        "number": account.number,
        "is_default_for_article_categories": bool(account.is_default_for_article_categories),
        "default_payment_type_ids": _default_payment_type_ids(db, account.id),
    }


def _get_account_or_404(db: Session, account_id: int) -> AccountingAccount:
    account = db.query(AccountingAccount).filter(AccountingAccount.id == account_id).first()
    if not account:
        raise api_error("accounting_account_not_found", status.HTTP_404_NOT_FOUND)
    return account


@router.get("/", response_model=List[AccountingAccountRead])
def list_accounting_accounts(
    organisation_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    accounts = (
        db.query(AccountingAccount)
        .filter(AccountingAccount.organisation_id == organisation_id)
        .order_by(AccountingAccount.number, AccountingAccount.name)
        .all()
    )
    return [_account_response(db, account) for account in accounts]


@router.get("/payment-type-defaults", response_model=List[PaymentTypeAccountDefaultRead])
def read_payment_type_account_defaults(
    organisation_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    payment_types = (
        db.query(PaymentType)
        .filter(PaymentType.is_active.is_(True))
        .order_by(PaymentType.sort_order, PaymentType.slug)
        .all()
    )
    existing = {
        row.payment_type_id: row.accounting_account_id
        for row in db.query(AccountingAccountPaymentTypeDefault)
        .filter(AccountingAccountPaymentTypeDefault.organisation_id == organisation_id)
        .all()
    }
    return [
        {
            "payment_type_id": pt.id,
            "payment_type_slug": pt.slug,
            "accounting_account_id": existing.get(pt.id),
        }
        for pt in payment_types
    ]


@router.put("/payment-type-defaults", response_model=List[PaymentTypeAccountDefaultRead])
def update_payment_type_account_defaults(
    body: PaymentTypeAccountDefaultsUpdate,
    organisation_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)

    seen_payment_types: set[int] = set()
    for item in body.defaults:
        if item.payment_type_id in seen_payment_types:
            raise api_error("payment_type_default_duplicate", status.HTTP_400_BAD_REQUEST)
        seen_payment_types.add(item.payment_type_id)
        get_payment_type_or_404(db, item.payment_type_id)
        if item.accounting_account_id is not None:
            ensure_accounting_account_for_org(db, item.accounting_account_id, organisation_id)

    db.query(AccountingAccountPaymentTypeDefault).filter(
        AccountingAccountPaymentTypeDefault.organisation_id == organisation_id
    ).delete(synchronize_session=False)

    for item in body.defaults:
        if item.accounting_account_id is None:
            continue
        db.add(
            AccountingAccountPaymentTypeDefault(
                organisation_id=organisation_id,
                payment_type_id=item.payment_type_id,
                accounting_account_id=item.accounting_account_id,
            )
        )
    db.commit()
    return read_payment_type_account_defaults(
        organisation_id=organisation_id,
        db=db,
        current_user=current_user,
        tenant=tenant,
    )


@router.get("/tax-code-defaults", response_model=List[TaxCodeAccountDefaultRead])
def read_tax_code_account_defaults(
    organisation_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    org = ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    tax_codes = (
        db.query(TaxCode)
        .filter(TaxCode.country_id == org.country_id)
        .order_by(TaxCode.name)
        .all()
    )
    existing = {
        row.tax_code_id: row.accounting_account_id
        for row in db.query(AccountingAccountTaxCodeDefault)
        .filter(AccountingAccountTaxCodeDefault.organisation_id == organisation_id)
        .all()
    }
    return [
        {
            "tax_code_id": tc.id,
            "tax_code_name": tc.name,
            "accounting_account_id": existing.get(tc.id),
        }
        for tc in tax_codes
    ]


@router.put("/tax-code-defaults", response_model=List[TaxCodeAccountDefaultRead])
def update_tax_code_account_defaults(
    body: TaxCodeAccountDefaultsUpdate,
    organisation_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)

    seen_tax_codes: set[int] = set()
    for item in body.defaults:
        if item.tax_code_id in seen_tax_codes:
            raise api_error("tax_code_default_duplicate", status.HTTP_400_BAD_REQUEST)
        seen_tax_codes.add(item.tax_code_id)
        ensure_tax_code_for_country(db, item.tax_code_id, org.country_id)
        if item.accounting_account_id is not None:
            ensure_accounting_account_for_org(db, item.accounting_account_id, organisation_id)

    db.query(AccountingAccountTaxCodeDefault).filter(
        AccountingAccountTaxCodeDefault.organisation_id == organisation_id
    ).delete(synchronize_session=False)

    for item in body.defaults:
        if item.accounting_account_id is None:
            continue
        db.add(
            AccountingAccountTaxCodeDefault(
                organisation_id=organisation_id,
                tax_code_id=item.tax_code_id,
                accounting_account_id=item.accounting_account_id,
            )
        )
    db.commit()
    return read_tax_code_account_defaults(
        organisation_id=organisation_id,
        db=db,
        current_user=current_user,
        tenant=tenant,
    )


@router.get("/{account_id}", response_model=AccountingAccountRead)
def read_accounting_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    account = _get_account_or_404(db, account_id)
    ensure_user_can_use_organisation(db, current_user, account.organisation_id, tenant.hire_company_id)
    return _account_response(db, account)


@router.post("/", response_model=AccountingAccountRead, status_code=status.HTTP_201_CREATED)
def create_accounting_account(
    body: AccountingAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, body.organisation_id)
    ensure_user_can_use_organisation(db, current_user, body.organisation_id, tenant.hire_company_id)

    if body.is_default_for_article_categories:
        clear_org_category_default_flag(db, body.organisation_id)

    account = AccountingAccount(
        organisation_id=body.organisation_id,
        name=body.name.strip(),
        number=body.number.strip(),
        is_default_for_article_categories=body.is_default_for_article_categories,
    )
    db.add(account)
    commit_or_raise(db, on_integrity=_raise_duplicate_account_number)
    db.refresh(account)
    return _account_response(db, account)


@router.put("/{account_id}", response_model=AccountingAccountRead)
def update_accounting_account(
    account_id: int,
    body: AccountingAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    account = _get_account_or_404(db, account_id)
    ensure_can_manage_organisation(current_user, account.organisation_id)
    ensure_user_can_use_organisation(db, current_user, account.organisation_id, tenant.hire_company_id)

    if body.name is not None:
        account.name = body.name.strip()
    if body.number is not None:
        account.number = body.number.strip()
    if body.is_default_for_article_categories is not None:
        if body.is_default_for_article_categories:
            clear_org_category_default_flag(db, account.organisation_id, except_id=account.id)
        account.is_default_for_article_categories = body.is_default_for_article_categories

    commit_or_raise(db, on_integrity=_raise_duplicate_account_number)
    db.refresh(account)
    return _account_response(db, account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_accounting_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    account = _get_account_or_404(db, account_id)
    ensure_can_manage_organisation(current_user, account.organisation_id)
    ensure_user_can_use_organisation(db, current_user, account.organisation_id, tenant.hire_company_id)
    assert_accounting_account_deletable(db, account_id)
    db.delete(account)
    db.commit()
    return None
