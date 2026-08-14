"""Cloud-admin SumUp connect for an organisation (API key primary; OAuth dormant)."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import sumup_client
from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n import t
from ..i18n.context import get_request_locale
from ..i18n.errors import api_error
from ..models import Organisation, SumupOAuthState, SumupReader, User
from ..sumup_client import sumup_error
from ..sumup_tokens import (
    apply_api_key,
    apply_merchant_details,
    apply_token_response,
    get_valid_access_token,
    oauth_state_expired,
)
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    get_current_tenant,
)

router = APIRouter()

OAUTH_STATE_TTL = timedelta(minutes=10)


class SumupConnectStatus(BaseModel):
    organisation_id: int
    connected: bool
    merchant_code: str | None = None
    merchant_name: str | None = None
    merchant_sandbox: bool | None = None
    merchant_country: str | None = None
    reader_count: int = 0
    payments_ready: bool = False


class SumupAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class SumupApiKeyBody(BaseModel):
    api_key: str = Field(min_length=1)
    merchant_code: str | None = Field(
        default=None,
        description="Required when the API key can access more than one SumUp merchant.",
    )


class SumupMerchantChoice(BaseModel):
    merchant_code: str
    merchant_name: str | None = None
    sandbox: bool | None = None
    country: str | None = None


def _status_response(db: Session, organisation: Organisation) -> SumupConnectStatus:
    connected = bool(organisation.sumup_merchant_code and organisation.sumup_access_token)
    reader_count = (
        db.query(SumupReader).filter(SumupReader.organisation_id == organisation.id).count()
    )
    return SumupConnectStatus(
        organisation_id=organisation.id,
        connected=connected,
        merchant_code=organisation.sumup_merchant_code if connected else None,
        merchant_name=organisation.sumup_merchant_name if connected else None,
        merchant_sandbox=organisation.sumup_merchant_sandbox if connected else None,
        merchant_country=organisation.sumup_merchant_country if connected else None,
        reader_count=reader_count,
        payments_ready=sumup_client.affiliate_key_configured(),
    )


def _refresh_merchant_details(db: Session, organisation: Organisation) -> None:
    """Best-effort name/sandbox for the *connected* merchant; status still works if this fails."""
    merchant_code = (organisation.sumup_merchant_code or "").strip()
    if not merchant_code or not organisation.sumup_access_token:
        return
    try:
        profile = sumup_client.get_merchant_profile_for_code(
            get_valid_access_token(db, organisation),
            merchant_code,
        )
    except Exception:
        return
    apply_merchant_details(organisation, profile)
    commit_or_raise(db)
    db.refresh(organisation)


def _frontend_return_url(*, connected: bool = False, error: str | None = None) -> str:
    base = (os.getenv("SUMUP_FRONTEND_RETURN_URL") or "").strip()
    if not base:
        base = "/sumup-devices"
    params: dict[str, str] = {}
    if connected:
        params["connected"] = "1"
    if error:
        params["error"] = error.strip()[:300]
    if not params:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode(params)}"


def _oauth_error_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(url=_frontend_return_url(error=message), status_code=302)


@router.get("/organisations/{organisation_id}/status", response_model=SumupConnectStatus)
def read_connect_status(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupConnectStatus:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    _refresh_merchant_details(db, organisation)
    return _status_response(db, organisation)


@router.put("/organisations/{organisation_id}/api-key", response_model=SumupConnectStatus)
def put_api_key(
    organisation_id: int,
    body: SumupApiKeyBody,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupConnectStatus:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)

    api_key = (body.api_key or "").strip()
    if not api_key:
        raise api_error("sumup_api_key_required", status.HTTP_400_BAD_REQUEST)

    try:
        memberships = sumup_client.list_merchant_memberships(api_key)
    except sumup_client.SumupApiError as exc:
        raise sumup_error(exc) from exc

    if not memberships:
        # Older credentials may lack memberships; fall back to /me default merchant.
        try:
            profile = sumup_client.get_merchant_profile(api_key)
        except sumup_client.SumupApiError as exc:
            raise sumup_error(exc) from exc
        memberships = [
            {
                "merchant_code": str(profile["merchant_code"]).strip(),
                "merchant_name": profile.get("merchant_name"),
                "sandbox": profile.get("sandbox"),
                "country": profile.get("country"),
            }
        ]

    by_code = {str(m["merchant_code"]).strip(): m for m in memberships if m.get("merchant_code")}
    existing = (organisation.sumup_merchant_code or "").strip()
    requested = (body.merchant_code or "").strip() or None

    if existing:
        if requested and requested != existing:
            raise api_error("sumup_merchant_mismatch", status.HTTP_400_BAD_REQUEST)
        merchant_code = existing
        if merchant_code not in by_code:
            raise api_error("sumup_merchant_mismatch", status.HTTP_400_BAD_REQUEST)
    elif requested:
        if requested not in by_code:
            raise api_error("sumup_merchant_not_accessible", status.HTTP_400_BAD_REQUEST)
        merchant_code = requested
    elif len(by_code) == 1:
        merchant_code = next(iter(by_code))
    else:
        locale = get_request_locale()
        merchants = [
            SumupMerchantChoice(
                merchant_code=str(m["merchant_code"]),
                merchant_name=m.get("merchant_name"),
                sandbox=m.get("sandbox"),
                country=m.get("country"),
            ).model_dump()
            for m in memberships
            if m.get("merchant_code")
        ]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "sumup_merchant_selection_required",
                "message": t("errors.sumup_merchant_selection_required", locale),
                "merchants": merchants,
            },
        )

    try:
        profile = sumup_client.get_merchant_profile_for_code(api_key, merchant_code)
    except sumup_client.SumupApiError as exc:
        raise sumup_error(exc) from exc

    membership = by_code.get(merchant_code) or {}
    # Prefer Merchant API sandbox when present; else membership is_test_account.
    sandbox = profile.get("sandbox")
    if sandbox is None and "sandbox" in membership:
        sandbox = membership.get("sandbox")
    name = profile.get("merchant_name") or membership.get("merchant_name")
    country = profile.get("country") or membership.get("country")

    apply_api_key(
        organisation,
        api_key=api_key,
        merchant_code=merchant_code,
        merchant_name=name,
        sandbox=sandbox,
        country=country,
    )
    commit_or_raise(db)
    db.refresh(organisation)
    return _status_response(db, organisation)


@router.post("/organisations/{organisation_id}/authorize", response_model=SumupAuthorizeResponse)
def start_oauth_authorize(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupAuthorizeResponse:
    ensure_can_manage_organisation(current_user, organisation_id)
    ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    try:
        _, _, redirect_uri = sumup_client.require_sumup_oauth_config()
    except sumup_client.SumupConfigError as exc:
        raise sumup_error(exc) from exc

    state = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    db.add(
        SumupOAuthState(
            state=state,
            organisation_id=organisation_id,
            user_id=current_user.id,
            created_at=now,
            expires_at=now + OAUTH_STATE_TTL,
        )
    )
    commit_or_raise(db)

    authorize_url = sumup_client.build_authorize_url(state=state, redirect_uri=redirect_uri)
    return SumupAuthorizeResponse(authorize_url=authorize_url, state=state)


@router.get("/oauth/callback")
def oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    locale = get_request_locale()
    if error:
        detail = (error_description or error).strip() or t("errors.sumup_oauth_denied", locale)
        return _oauth_error_redirect(detail)

    if not code or not state:
        return _oauth_error_redirect(t("errors.sumup_oauth_missing_code", locale))

    oauth_state = db.query(SumupOAuthState).filter(SumupOAuthState.state == state).first()
    if not oauth_state or oauth_state_expired(oauth_state.expires_at):
        return _oauth_error_redirect(t("errors.sumup_oauth_invalid_state", locale))

    organisation = db.query(Organisation).filter(Organisation.id == oauth_state.organisation_id).first()
    if not organisation:
        return _oauth_error_redirect(t("errors.organisation_not_found", locale))

    try:
        _, _, redirect_uri = sumup_client.require_sumup_oauth_config()
        tokens = sumup_client.exchange_code_for_tokens(code, redirect_uri)
        profile = sumup_client.get_merchant_profile(tokens["access_token"])
    except sumup_client.SumupConfigError:
        return _oauth_error_redirect(t("errors.sumup_oauth_config", locale))
    except sumup_client.SumupApiError as exc:
        detail = sumup_client.sumup_detail_message(exc.detail)
        return _oauth_error_redirect(
            t("errors.sumup_request_failed", locale, detail=detail),
        )

    organisation.sumup_merchant_code = profile["merchant_code"]
    apply_token_response(organisation, tokens)
    apply_merchant_details(organisation, profile)
    organisation.sumup_connected_at = datetime.now(UTC)
    db.delete(oauth_state)
    commit_or_raise(db)

    return RedirectResponse(url=_frontend_return_url(connected=True), status_code=302)


@router.post("/organisations/{organisation_id}/disconnect", response_model=SumupConnectStatus)
def disconnect_sumup(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupConnectStatus:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)

    db.query(SumupReader).filter(SumupReader.organisation_id == organisation.id).delete()
    organisation.sumup_merchant_code = None
    organisation.sumup_merchant_name = None
    organisation.sumup_merchant_sandbox = None
    organisation.sumup_merchant_country = None
    organisation.sumup_access_token = None
    organisation.sumup_refresh_token = None
    organisation.sumup_token_expires_at = None
    organisation.sumup_connected_at = None
    commit_or_raise(db)
    db.refresh(organisation)
    return _status_response(db, organisation)
