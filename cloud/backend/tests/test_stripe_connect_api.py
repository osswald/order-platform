"""Stripe Connect HTTP API."""

from unittest.mock import MagicMock, patch

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code, stripe_account_payload, stripe_object

client = TestClient(app)


def _seed_tenant() -> int:
    db = SessionLocal()
    try:
        hc = HireCompany(name="Stripe Connect HC")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Stripe Connect Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="stripe-connect@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id
    finally:
        db.close()


def _auth_headers() -> dict[str, str]:
    r = client.post("/auth/token", data={"username": "stripe-connect@test.local", "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_connect_status_for_organisation():
    org_id = _seed_tenant()
    r = client.get(
        f"/stripe/connect/organisations/{org_id}/status",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organisation_id"] == org_id
    assert body["stripe_account_id"] is None
    assert body["charges_enabled"] is False


def _stripe_v2_client(account_payload: dict, link_url: str) -> MagicMock:
    stripe_sdk = MagicMock()
    account = stripe_object({**account_payload, "id": "acct_new123"})
    stripe_sdk.v2.core.accounts.create.return_value = account
    stripe_sdk.v2.core.accounts.retrieve.return_value = account
    stripe_sdk.v2.core.account_links.create.return_value = stripe_object({"url": link_url})
    return stripe_sdk


def test_create_account_link(monkeypatch):
    org_id = _seed_tenant()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_CONNECT_RETURN_URL", "https://app.test/return")
    monkeypatch.setenv("STRIPE_CONNECT_REFRESH_URL", "https://app.test/refresh")

    stripe_sdk = _stripe_v2_client(
        stripe_account_payload("v2_account_not_ready"),
        "https://connect.stripe.com/setup/test",
    )

    with (
        patch("app.stripe_client.stripe.StripeClient", return_value=stripe_sdk),
        patch("app.stripe_client.stripe.Account.create") as v1_account_create,
    ):
        r = client.post(
            f"/stripe/connect/organisations/{org_id}/account-link",
            headers=_auth_headers(),
            json={
                "return_url": "https://evil.example/phish",
                "refresh_url": "https://evil.example/phish2",
            },
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"] == "https://connect.stripe.com/setup/test"
    assert body["stripe_account_id"] == "acct_new123"
    assert body["charges_enabled"] is False

    v1_account_create.assert_not_called()
    create_params = stripe_sdk.v2.core.accounts.create.call_args.args[0]
    assert "type" not in create_params
    assert create_params["configuration"]["merchant"]["capabilities"]["card_payments"]["requested"] is True
    assert create_params["metadata"]["organisation_id"] == str(org_id)

    onboarding = stripe_sdk.v2.core.account_links.create.call_args.args[0]["use_case"]["account_onboarding"]
    assert onboarding["return_url"] == "https://app.test/return"
    assert onboarding["refresh_url"] == "https://app.test/refresh"


def test_refresh_marks_organisation_ready_when_capabilities_active(monkeypatch):
    org_id = _seed_tenant()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_CONNECT_RETURN_URL", "https://app.test/return")
    monkeypatch.setenv("STRIPE_CONNECT_REFRESH_URL", "https://app.test/refresh")

    not_ready = _stripe_v2_client(stripe_account_payload("v2_account_not_ready"), "https://connect.stripe.com/x")
    with patch("app.stripe_client.stripe.StripeClient", return_value=not_ready):
        first = client.post(
            f"/stripe/connect/organisations/{org_id}/account-link",
            headers=_auth_headers(),
            json={},
        )
    assert first.status_code == 200, first.text
    assert first.json()["charges_enabled"] is False

    ready = _stripe_v2_client(stripe_account_payload("v2_account_ready"), "https://connect.stripe.com/x")
    with patch("app.stripe_client.stripe.StripeClient", return_value=ready):
        r = client.post(
            f"/stripe/connect/organisations/{org_id}/refresh",
            headers=_auth_headers(),
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["charges_enabled"] is True
    assert body["payouts_enabled"] is True
    assert body["details_submitted"] is True


def test_account_link_requires_stripe_secret_key(monkeypatch):
    org_id = _seed_tenant()
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("STRIPE_CONNECT_RETURN_URL", "https://app.test/return")
    monkeypatch.setenv("STRIPE_CONNECT_REFRESH_URL", "https://app.test/refresh")

    r = client.post(
        f"/stripe/connect/organisations/{org_id}/account-link",
        headers=_auth_headers(),
        json={},
    )
    assert r.status_code == 503, r.text
