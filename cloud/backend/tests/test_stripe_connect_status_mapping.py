"""Mapping Stripe account payloads onto Organisation readiness flags."""

import pytest
from app.models import Organisation
from app.stripe_connect_status import update_organisation_from_stripe_account

from tests.helpers import stripe_account_payload as _load
from tests.helpers import stripe_object


@pytest.fixture(params=["dict", "object"])
def shape(request):
    return (lambda data: data) if request.param == "dict" else stripe_object


def _org() -> Organisation:
    return Organisation(
        name="Mapping Org",
        stripe_charges_enabled=False,
        stripe_payouts_enabled=False,
        stripe_details_submitted=False,
    )


def test_v2_account_before_onboarding_is_not_ready(shape):
    org = _org()
    update_organisation_from_stripe_account(org, shape(_load("v2_account_not_ready")))

    assert org.stripe_charges_enabled is False
    assert org.stripe_payouts_enabled is False
    assert org.stripe_details_submitted is False
    assert org.stripe_account_updated_at is not None


def test_v2_account_with_active_capabilities_is_ready(shape):
    org = _org()
    update_organisation_from_stripe_account(org, shape(_load("v2_account_ready")))

    assert org.stripe_charges_enabled is True
    assert org.stripe_payouts_enabled is True
    assert org.stripe_details_submitted is True


def test_active_card_payments_with_open_requirements_still_charges(shape):
    data = _load("v2_account_ready")
    data["requirements"]["entries"] = [
        {"awaiting_action_from": "user", "description": "external_account", "minimum_deadline": {"status": "currently_due"}}
    ]
    org = _org()
    update_organisation_from_stripe_account(org, shape(data))

    assert org.stripe_charges_enabled is True
    assert org.stripe_details_submitted is False


def test_requirements_awaiting_stripe_do_not_block_details_submitted(shape):
    data = _load("v2_account_ready")
    data["requirements"]["entries"] = [
        {"awaiting_action_from": "stripe", "description": "review", "minimum_deadline": {"status": "currently_due"}}
    ]
    org = _org()
    update_organisation_from_stripe_account(org, shape(data))

    assert org.stripe_details_submitted is True


def test_v1_account_snapshot_still_maps(shape):
    """`account.updated` webhooks deliver a v1-shaped snapshot."""
    org = _org()
    update_organisation_from_stripe_account(
        org,
        shape(
            {
                "id": "acct_v1_legacy",
                "charges_enabled": True,
                "payouts_enabled": True,
                "details_submitted": True,
            }
        ),
    )

    assert org.stripe_charges_enabled is True
    assert org.stripe_payouts_enabled is True
    assert org.stripe_details_submitted is True
