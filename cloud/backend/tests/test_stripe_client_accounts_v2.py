"""Stripe Accounts v2 client wrapper."""

from unittest.mock import MagicMock, patch

import pytest
from app import stripe_client


@pytest.fixture(autouse=True)
def _stripe_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")


@pytest.fixture
def v2_client():
    client = MagicMock()
    with patch("app.stripe_client.stripe.StripeClient", return_value=client):
        yield client


def test_create_connected_account_uses_accounts_v2(v2_client):
    with patch("app.stripe_client.stripe.Account.create") as v1_create:
        stripe_client.create_connected_account(
            organisation_id=7,
            hire_company_id=3,
            name="Vendiqo Test Org",
            country="ch",
            currency="CHF",
        )

    v1_create.assert_not_called()
    v2_client.v2.core.accounts.create.assert_called_once()
    params = v2_client.v2.core.accounts.create.call_args.args[0]

    assert "type" not in params
    assert params["dashboard"] == "full"
    assert params["display_name"] == "Vendiqo Test Org"
    assert params["identity"]["country"] == "CH"
    assert params["identity"]["entity_type"] == "company"
    assert params["identity"]["business_details"]["registered_name"] == "Vendiqo Test Org"
    assert params["defaults"]["currency"] == "chf"
    assert params["defaults"]["responsibilities"] == {
        "fees_collector": "stripe",
        "losses_collector": "stripe",
    }
    assert params["configuration"]["merchant"]["capabilities"]["card_payments"]["requested"] is True
    assert params["metadata"] == {"organisation_id": "7", "hire_company_id": "3"}
    assert "configuration.merchant" in params["include"]
    assert "requirements" in params["include"]


def test_create_connected_account_defaults_country_and_currency(v2_client):
    stripe_client.create_connected_account(
        organisation_id=1,
        hire_company_id=1,
        name="No Country Org",
        country=None,
        currency=None,
    )

    params = v2_client.v2.core.accounts.create.call_args.args[0]
    assert params["identity"]["country"] == "CH"
    assert params["defaults"]["currency"] == "chf"


def test_create_account_link_uses_v2_onboarding_use_case(v2_client):
    with patch("app.stripe_client.stripe.AccountLink.create") as v1_link:
        stripe_client.create_account_link(
            account_id="acct_v2_test",
            return_url="https://app.test/return",
            refresh_url="https://app.test/refresh",
        )

    v1_link.assert_not_called()
    params = v2_client.v2.core.account_links.create.call_args.args[0]
    assert params["account"] == "acct_v2_test"
    assert params["use_case"]["type"] == "account_onboarding"
    onboarding = params["use_case"]["account_onboarding"]
    assert onboarding["configurations"] == ["merchant"]
    assert onboarding["return_url"] == "https://app.test/return"
    assert onboarding["refresh_url"] == "https://app.test/refresh"


def test_retrieve_account_requests_merchant_configuration(v2_client):
    with patch("app.stripe_client.stripe.Account.retrieve") as v1_retrieve:
        stripe_client.retrieve_account("acct_v2_test")

    v1_retrieve.assert_not_called()
    call = v2_client.v2.core.accounts.retrieve.call_args
    assert call.args[0] == "acct_v2_test"
    include = call.args[1]["include"]
    assert "configuration.merchant" in include
    assert "requirements" in include


def test_connect_calls_require_secret_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    with pytest.raises(stripe_client.StripeConfigError):
        stripe_client.create_connected_account(
            organisation_id=1,
            hire_company_id=1,
            name="Org",
            country="CH",
        )
