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


def get_valid_access_token(db: Session, organisation: Organisation) -> str:
    token = (organisation.sumup_access_token or "").strip()
    expires_at = _as_utc(organisation.sumup_token_expires_at)
    if token and expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=1):
        return token
    refresh_token = (organisation.sumup_refresh_token or "").strip()
    if not refresh_token:
        raise sumup_client.SumupConfigError("SumUp is not connected for this organisation")
    tokens = sumup_client.refresh_access_token(refresh_token)
    apply_token_response(organisation, tokens)
    commit_or_raise(db)
    db.refresh(organisation)
    access_token = (organisation.sumup_access_token or "").strip()
    if not access_token:
        raise sumup_client.SumupApiError(502, "SumUp token refresh did not return access_token")
    return access_token
