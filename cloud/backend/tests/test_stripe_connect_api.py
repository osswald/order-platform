"""Stripe Connect HTTP API."""

from unittest.mock import MagicMock, patch

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

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


@patch("app.routers.stripe_connect.stripe_client.create_connected_account")
@patch("app.routers.stripe_connect.stripe_client.create_account_link")
def test_create_account_link(mock_link, mock_create_account, monkeypatch):
    org_id = _seed_tenant()
    monkeypatch.setenv("STRIPE_CONNECT_RETURN_URL", "https://app.test/return")
    monkeypatch.setenv("STRIPE_CONNECT_REFRESH_URL", "https://app.test/refresh")

    account = MagicMock()
    account.id = "acct_new123"
    account.charges_enabled = False
    account.payouts_enabled = False
    account.details_submitted = False
    mock_create_account.return_value = account

    link = MagicMock()
    link.url = "https://connect.stripe.com/setup/test"
    mock_link.return_value = link

    r = client.post(
        f"/stripe/connect/organisations/{org_id}/account-link",
        headers=_auth_headers(),
        json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"] == "https://connect.stripe.com/setup/test"
    assert body["stripe_account_id"] == "acct_new123"
