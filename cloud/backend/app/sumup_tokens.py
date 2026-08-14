"""Persist and refresh organisation SumUp OAuth tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from . import sumup_client
from .db_errors import commit_or_raise
from .models import Organisation


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def oauth_state_expired(expires_at: datetime | None) -> bool:
    normalized = _as_utc(expires_at)
    if normalized is None:
        return True
    return normalized <= datetime.now(UTC)


def apply_token_response(organisation: Organisation, tokens: dict) -> None:
    organisation.sumup_access_token = tokens.get("access_token")
    if tokens.get("refresh_token"):
        organisation.sumup_refresh_token = tokens["refresh_token"]
    expires_in = tokens.get("expires_in")
    if isinstance(expires_in, int):
        organisation.sumup_token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)


def apply_api_key(
    organisation: Organisation,
    *,
    api_key: str,
    merchant_code: str,
    merchant_name: str | None = None,
    sandbox: bool | None = None,
    country: str | None = None,
) -> None:
    """Persist a static merchant API key (clears OAuth refresh/expiry)."""
    organisation.sumup_access_token = api_key
    organisation.sumup_refresh_token = None
    organisation.sumup_token_expires_at = None
    organisation.sumup_merchant_code = merchant_code
    organisation.sumup_merchant_name = merchant_name
    organisation.sumup_merchant_sandbox = sandbox
    organisation.sumup_merchant_country = country
    organisation.sumup_connected_at = datetime.now(UTC)


def apply_merchant_details(organisation: Organisation, profile: dict) -> None:
    """Refresh name/sandbox/country only — never change the connected merchant_code.

    API keys can access multiple merchants; ``/me`` returns the default live one.
    Merchant identity must stay on the value chosen at connect time.
    """
    if "merchant_name" in profile:
        organisation.sumup_merchant_name = profile.get("merchant_name")
    if "sandbox" in profile:
        organisation.sumup_merchant_sandbox = profile.get("sandbox")
    if "country" in profile:
        organisation.sumup_merchant_country = profile.get("country")


def get_valid_access_token(db: Session, organisation: Organisation) -> str:
    token = (organisation.sumup_access_token or "").strip()
    refresh_token = (organisation.sumup_refresh_token or "").strip()
    # API-key mode: no refresh token — use stored credential as static Bearer.
    if not refresh_token:
        if token:
            return token
        raise sumup_client.SumupConfigError("SumUp is not connected for this organisation")
    expires_at = _as_utc(organisation.sumup_token_expires_at)
    if token and expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=1):
        return token
    tokens = sumup_client.refresh_access_token(refresh_token)
    apply_token_response(organisation, tokens)
    commit_or_raise(db)
    db.refresh(organisation)
    access_token = (organisation.sumup_access_token or "").strip()
    if not access_token:
        raise sumup_client.SumupApiError(502, "SumUp token refresh did not return access_token")
    return access_token
