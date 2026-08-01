"""Cloud-admin SumUp OAuth connect for an organisation."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import sumup_client
from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n import t
from ..i18n.context import get_request_locale
from ..models import Organisation, SumupOAuthState, SumupReader, User
from ..sumup_client import sumup_error
from ..sumup_tokens import apply_token_response, oauth_state_expired
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
    reader_count: int = 0


class SumupAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


def _status_response(db: Session, organisation: Organisation) -> SumupConnectStatus:
    connected = bool(organisation.sumup_merchant_code and organisation.sumup_access_token)
    reader_count = (
        db.query(SumupReader).filter(SumupReader.organisation_id == organisation.id).count()
    )
    return SumupConnectStatus(
        organisation_id=organisation.id,
        connected=connected,
        merchant_code=organisation.sumup_merchant_code if connected else None,
        reader_count=reader_count,
    )


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
    organisation.sumup_access_token = None
    organisation.sumup_refresh_token = None
    organisation.sumup_token_expires_at = None
    organisation.sumup_connected_at = None
    commit_or_raise(db)
    db.refresh(organisation)
    return _status_response(db, organisation)
