"""Cloud-admin Stripe Connect onboarding for a Verleiher."""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import HireCompany
from ..stripe_client import StripeConfigError
from .. import stripe_client
from ..tenancy import TenantContext, get_current_tenant_admin

router = APIRouter()


class StripeConnectStatus(BaseModel):
    hire_company_id: int
    stripe_account_id: str | None = None
    charges_enabled: bool = False
    payouts_enabled: bool = False
    details_submitted: bool = False
    onboarding_started_at: datetime | None = None
    account_updated_at: datetime | None = None


class StripeAccountLinkRequest(BaseModel):
    return_url: str = Field(..., min_length=1)
    refresh_url: str = Field(..., min_length=1)


class StripeAccountLinkResponse(StripeConnectStatus):
    url: str


def _stripe_error(exc: Exception) -> HTTPException:
    if isinstance(exc, StripeConfigError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, stripe.error.StripeError):
        message = getattr(exc, "user_message", None) or str(exc)
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe request failed")


def _update_connect_status(company: HireCompany, account) -> None:
    company.stripe_charges_enabled = bool(getattr(account, "charges_enabled", False))
    company.stripe_payouts_enabled = bool(getattr(account, "payouts_enabled", False))
    company.stripe_details_submitted = bool(getattr(account, "details_submitted", False))
    company.stripe_account_updated_at = datetime.now(timezone.utc)


def _status_response(company: HireCompany) -> StripeConnectStatus:
    return StripeConnectStatus(
        hire_company_id=company.id,
        stripe_account_id=company.stripe_account_id,
        charges_enabled=bool(company.stripe_charges_enabled),
        payouts_enabled=bool(company.stripe_payouts_enabled),
        details_submitted=bool(company.stripe_details_submitted),
        onboarding_started_at=company.stripe_onboarding_started_at,
        account_updated_at=company.stripe_account_updated_at,
    )


@router.get("/status", response_model=StripeConnectStatus)
def read_connect_status(
    tenant: TenantContext = Depends(get_current_tenant_admin),
) -> StripeConnectStatus:
    return _status_response(tenant.hire_company)


@router.post("/account-link", response_model=StripeAccountLinkResponse)
def create_connect_account_link(
    body: StripeAccountLinkRequest,
    tenant: TenantContext = Depends(get_current_tenant_admin),
    db: Session = Depends(get_db),
) -> StripeAccountLinkResponse:
    company = tenant.hire_company
    try:
        if not company.stripe_account_id:
            account = stripe_client.create_connected_account(
                hire_company_id=company.id,
                name=company.name,
                country=company.country,
            )
            company.stripe_account_id = account.id
            _update_connect_status(company, account)

        link = stripe_client.create_account_link(
            account_id=company.stripe_account_id,
            return_url=body.return_url,
            refresh_url=body.refresh_url,
        )
    except Exception as exc:
        raise _stripe_error(exc) from exc

    company.stripe_onboarding_started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(company)
    return StripeAccountLinkResponse(**_status_response(company).model_dump(), url=link.url)


@router.post("/refresh", response_model=StripeConnectStatus)
def refresh_connect_status(
    tenant: TenantContext = Depends(get_current_tenant_admin),
    db: Session = Depends(get_db),
) -> StripeConnectStatus:
    company = tenant.hire_company
    if not company.stripe_account_id:
        return _status_response(company)
    try:
        account = stripe_client.retrieve_account(company.stripe_account_id)
    except Exception as exc:
        raise _stripe_error(exc) from exc
    _update_connect_status(company, account)
    db.commit()
    db.refresh(company)
    return _status_response(company)
