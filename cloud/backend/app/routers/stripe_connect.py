"""Cloud-admin Stripe Connect onboarding for an organisation."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from ..i18n.errors import api_error
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..db_errors import commit_or_raise
from ..models import Organisation, User
from ..stripe_client import StripeConfigError, stripe_error
from .. import stripe_client
from ..stripe_connect_status import update_organisation_from_stripe_account
from ..auth_deps import get_current_user
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    get_current_tenant,
)

router = APIRouter()


class StripeConnectStatus(BaseModel):
    organisation_id: int
    hire_company_id: int
    stripe_account_id: str | None = None
    charges_enabled: bool = False
    payouts_enabled: bool = False
    details_submitted: bool = False
    onboarding_started_at: datetime | None = None
    account_updated_at: datetime | None = None


class StripeAccountLinkRequest(BaseModel):
    return_url: str | None = Field(None, min_length=1)
    refresh_url: str | None = Field(None, min_length=1)


class StripeAccountLinkResponse(StripeConnectStatus):
    url: str

def _status_response(organisation: Organisation) -> StripeConnectStatus:
    return StripeConnectStatus(
        organisation_id=organisation.id,
        hire_company_id=organisation.hire_company_id,
        stripe_account_id=organisation.stripe_account_id,
        charges_enabled=bool(organisation.stripe_charges_enabled),
        payouts_enabled=bool(organisation.stripe_payouts_enabled),
        details_submitted=bool(organisation.stripe_details_submitted),
        onboarding_started_at=organisation.stripe_onboarding_started_at,
        account_updated_at=organisation.stripe_account_updated_at,
    )


def _account_link_url(value: str | None, env_name: str) -> str:
    url = (value or os.getenv(env_name) or "").strip()
    if not url:
        raise api_error("env_required", status.HTTP_422_UNPROCESSABLE_CONTENT, env_name=env_name)
    return url


@router.get("/organisations/{organisation_id}/status", response_model=StripeConnectStatus)
def read_connect_status(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> StripeConnectStatus:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    return _status_response(organisation)


@router.post("/organisations/{organisation_id}/account-link", response_model=StripeAccountLinkResponse)
def create_connect_account_link(
    organisation_id: int,
    body: StripeAccountLinkRequest,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> StripeAccountLinkResponse:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    try:
        if not organisation.stripe_account_id:
            account = stripe_client.create_connected_account(
                organisation_id=organisation.id,
                hire_company_id=organisation.hire_company_id,
                name=organisation.name,
                country=organisation.country.code if organisation.country else "CH",
            )
            organisation.stripe_account_id = account.id
            update_organisation_from_stripe_account(organisation, account)

        link = stripe_client.create_account_link(
            account_id=organisation.stripe_account_id,
            return_url=_account_link_url(body.return_url, "STRIPE_CONNECT_RETURN_URL"),
            refresh_url=_account_link_url(body.refresh_url, "STRIPE_CONNECT_REFRESH_URL"),
        )
    except Exception as exc:
        raise stripe_error(exc) from exc

    organisation.stripe_onboarding_started_at = datetime.now(timezone.utc)
    commit_or_raise(db)
    db.refresh(organisation)
    return StripeAccountLinkResponse(**_status_response(organisation).model_dump(), url=link.url)


@router.post("/organisations/{organisation_id}/refresh", response_model=StripeConnectStatus)
def refresh_connect_status(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> StripeConnectStatus:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    if not organisation.stripe_account_id:
        return _status_response(organisation)
    try:
        account = stripe_client.retrieve_account(organisation.stripe_account_id)
    except Exception as exc:
        raise stripe_error(exc) from exc
    update_organisation_from_stripe_account(organisation, account)
    commit_or_raise(db)
    db.refresh(organisation)
    return _status_response(organisation)
