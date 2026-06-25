"""Shared helpers for Stripe Connect account status on Organisation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .models import Organisation


def update_organisation_from_stripe_account(organisation: Organisation, account: Any) -> None:
    organisation.stripe_charges_enabled = bool(getattr(account, "charges_enabled", False))
    organisation.stripe_payouts_enabled = bool(getattr(account, "payouts_enabled", False))
    organisation.stripe_details_submitted = bool(getattr(account, "details_submitted", False))
    organisation.stripe_account_updated_at = datetime.now(UTC)


def update_organisation_from_stripe_account_dict(organisation: Organisation, data: dict[str, Any]) -> None:
    organisation.stripe_charges_enabled = bool(data.get("charges_enabled", False))
    organisation.stripe_payouts_enabled = bool(data.get("payouts_enabled", False))
    organisation.stripe_details_submitted = bool(data.get("details_submitted", False))
    organisation.stripe_account_updated_at = datetime.now(UTC)
