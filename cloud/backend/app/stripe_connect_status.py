"""Shared helpers for Stripe Connect account status on Organisation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .models import Organisation

BLOCKING_DEADLINE_STATUSES = {"currently_due", "past_due"}


def _field(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _path(source: Any, *keys: str) -> Any:
    for key in keys:
        source = _field(source, key)
        if source is None:
            return None
    return source


def _is_active(capability: Any) -> bool:
    return str(_field(capability, "status", "")) == "active"


def _has_blocking_requirements(account: Any) -> bool:
    entries = _path(account, "requirements", "entries")
    if not isinstance(entries, list | tuple):
        return False
    return any(
        _field(entry, "awaiting_action_from") == "user"
        and str(_path(entry, "minimum_deadline", "status") or "") in BLOCKING_DEADLINE_STATUSES
        for entry in entries
    )


def update_organisation_from_stripe_account(organisation: Organisation, account: Any) -> None:
    """Map an Accounts v2 account (or a v1 `account.updated` snapshot) onto the org flags."""
    capabilities = _path(account, "configuration", "merchant", "capabilities")
    if capabilities is not None:
        organisation.stripe_charges_enabled = _is_active(_field(capabilities, "card_payments"))
        organisation.stripe_payouts_enabled = _is_active(_path(capabilities, "stripe_balance", "payouts"))
        organisation.stripe_details_submitted = not _has_blocking_requirements(account)
    else:
        organisation.stripe_charges_enabled = bool(_field(account, "charges_enabled", False))
        organisation.stripe_payouts_enabled = bool(_field(account, "payouts_enabled", False))
        organisation.stripe_details_submitted = bool(_field(account, "details_submitted", False))
    organisation.stripe_account_updated_at = datetime.now(UTC)


def update_organisation_from_stripe_account_dict(organisation: Organisation, data: dict[str, Any]) -> None:
    update_organisation_from_stripe_account(organisation, data)
