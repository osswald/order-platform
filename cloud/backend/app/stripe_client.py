"""Small Stripe SDK wrapper for Connect and Terminal operations."""

from __future__ import annotations

import os
from typing import Any

import stripe

STRIPE_API_VERSION = "2026-04-22.dahlia"


class StripeConfigError(RuntimeError):
    """Raised when Stripe is not configured for the cloud backend."""


def _api_key() -> str:
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        raise StripeConfigError("STRIPE_SECRET_KEY is not configured")
    return key


def _configure() -> None:
    stripe.api_key = _api_key()
    stripe.api_version = STRIPE_API_VERSION


def create_connected_account(*, hire_company_id: int, name: str, country: str | None) -> Any:
    _configure()
    return stripe.Account.create(
        type="express",
        country=(country or "CH").upper(),
        business_type="company",
        business_profile={"name": name},
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
        metadata={"hire_company_id": str(hire_company_id)},
    )


def create_account_link(*, account_id: str, return_url: str, refresh_url: str) -> Any:
    _configure()
    return stripe.AccountLink.create(
        account=account_id,
        type="account_onboarding",
        return_url=return_url,
        refresh_url=refresh_url,
    )


def retrieve_account(account_id: str) -> Any:
    _configure()
    return stripe.Account.retrieve(account_id)


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
