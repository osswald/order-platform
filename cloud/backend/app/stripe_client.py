"""Small Stripe SDK wrapper for Connect and Terminal operations."""

from __future__ import annotations

import os
from typing import Any

import stripe
from fastapi import HTTPException, status

from .i18n.errors import api_error

STRIPE_API_VERSION = "2026-04-22.dahlia"

# Accounts v2 fields the Connect flow needs back from create/retrieve.
ACCOUNT_INCLUDE = ["configuration.merchant", "defaults", "identity", "requirements"]

DEFAULT_PLATFORM_FEE_BPS = 20


class StripeConfigError(RuntimeError):
    """Raised when Stripe is not configured for the cloud backend."""


def stripe_error(exc: Exception) -> HTTPException:
    if isinstance(exc, StripeConfigError):
        return api_error("validation_failed", status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(exc, stripe.error.StripeError):
        return api_error("stripe_request_failed", status.HTTP_502_BAD_GATEWAY)
    return api_error("stripe_request_failed", status.HTTP_502_BAD_GATEWAY)


def _api_key() -> str:
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        raise StripeConfigError("STRIPE_SECRET_KEY is not configured")
    return key


def _configure() -> None:
    stripe.api_key = _api_key()
    stripe.api_version = STRIPE_API_VERSION


def _v2_client() -> Any:
    """Client for the v2 core APIs, which the module-level `stripe.*` helpers do not expose."""
    return stripe.StripeClient(api_key=_api_key())


def create_connected_account(
    *,
    organisation_id: int,
    hire_company_id: int,
    name: str,
    country: str | None,
    currency: str | None = None,
) -> Any:
    return _v2_client().v2.core.accounts.create(
        {
            "display_name": name,
            "dashboard": "full",
            "identity": {
                "country": (country or "CH").upper(),
                "entity_type": "company",
                "business_details": {"registered_name": name},
            },
            "defaults": {
                "currency": (currency or "CHF").lower(),
                "responsibilities": {
                    "fees_collector": "stripe",
                    "losses_collector": "stripe",
                },
            },
            "configuration": {"merchant": {"capabilities": {"card_payments": {"requested": True}}}},
            "metadata": {
                "organisation_id": str(organisation_id),
                "hire_company_id": str(hire_company_id),
            },
            "include": ACCOUNT_INCLUDE,
        }
    )


def create_account_link(*, account_id: str, return_url: str, refresh_url: str) -> Any:
    return _v2_client().v2.core.account_links.create(
        {
            "account": account_id,
            "use_case": {
                "type": "account_onboarding",
                "account_onboarding": {
                    "configurations": ["merchant"],
                    "return_url": return_url,
                    "refresh_url": refresh_url,
                },
            },
        }
    )


def retrieve_account(account_id: str) -> Any:
    return _v2_client().v2.core.accounts.retrieve(account_id, {"include": ACCOUNT_INCLUDE})


def platform_fee_bps() -> int:
    raw = (os.getenv("STRIPE_PLATFORM_FEE_BPS") or "").strip()
    if not raw:
        return DEFAULT_PLATFORM_FEE_BPS
    try:
        bps = int(raw)
    except ValueError:
        return DEFAULT_PLATFORM_FEE_BPS
    return bps if bps >= 0 else DEFAULT_PLATFORM_FEE_BPS


def platform_fee_cents(amount_cents: int, *, bps: int | None = None) -> int:
    """Platform take on a connected-account charge, rounded half-up to the minor unit."""
    rate = platform_fee_bps() if bps is None else bps
    if amount_cents <= 0 or rate <= 0:
        return 0
    fee = (amount_cents * rate + 5_000) // 10_000
    return min(fee, amount_cents - 1)


def create_terminal_connection_token(*, account_id: str) -> Any:
    _configure()
    return stripe.terminal.ConnectionToken.create(stripe_account=account_id)


def create_terminal_payment_intent(
    *,
    account_id: str,
    amount_cents: int,
    currency: str,
    metadata: dict[str, str],
    idempotency_key: str | None = None,
) -> Any:
    _configure()
    options: dict[str, Any] = {"stripe_account": account_id}
    if idempotency_key:
        options["idempotency_key"] = idempotency_key
    fee_cents = platform_fee_cents(amount_cents)
    if fee_cents > 0:
        options["application_fee_amount"] = fee_cents
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency.lower(),
        payment_method_types=["card_present"],
        capture_method="automatic",
        metadata=metadata,
        **options,
    )


def retrieve_terminal_payment_intent(*, account_id: str, payment_intent_id: str) -> Any:
    _configure()
    return stripe.PaymentIntent.retrieve(payment_intent_id, stripe_account=account_id)
