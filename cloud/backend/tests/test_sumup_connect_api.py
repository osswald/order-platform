"""SumUp OAuth connect HTTP API."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, SumupOAuthState, SumupReader, User
from app.roles import ROLE_MEMBER, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from app.sumup_tokens import oauth_state_expired
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed_tenant(*, connected: bool = False) -> int:
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"SumUp Connect HC {uuid4().hex[:8]}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="SumUp Connect Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        if connected:
            org.sumup_merchant_code = "MK10CL2A"
            org.sumup_access_token = "access_test"
            org.sumup_refresh_token = "refresh_test"
            org.sumup_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
            org.sumup_connected_at = datetime.now(UTC)
        db.add(org)
        db.flush()
        if connected:
            db.add(
                SumupReader(
                    organisation_id=org.id,
                    sumup_reader_id="rdr_test1234567890123456789012",
                    label="Front counter",
                    status="paired",
                )
            )
        db.add(
            User(
                email=f"sumup-connect-{uuid4().hex[:8]}@test.local",
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
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email.like("sumup-connect-%@test.local"))
            .order_by(User.id.desc())
            .first()
        )
        email = user.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _member_headers(org_id: int) -> dict[str, str]:
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        member = User(
            email=f"sumup-member-{uuid4().hex[:8]}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        member.organisations = [org]
        db.add(member)
        db.commit()
        email = member.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_connect_status_when_disconnected():
    org_id = _seed_tenant()
    r = client.get(
        f"/sumup/organisations/{org_id}/status",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organisation_id"] == org_id
    assert body["connected"] is False
    assert body["merchant_code"] is None
    assert body["reader_count"] == 0


def test_connect_status_when_connected():
    org_id = _seed_tenant(connected=True)
    r = client.get(
        f"/sumup/organisations/{org_id}/status",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["connected"] is True
    assert body["merchant_code"] == "MK10CL2A"
    assert body["reader_count"] == 1


def test_authorize_returns_url_when_env_set(monkeypatch):
    org_id = _seed_tenant()
    monkeypatch.setenv("SUMUP_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("SUMUP_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SUMUP_REDIRECT_URI", "https://admin.test/sumup/oauth/callback")

    r = client.post(
        f"/sumup/organisations/{org_id}/authorize",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "authorize_url" in body
    assert "state" in body
    assert body["authorize_url"].startswith("https://api.sumup.com/authorize")
    assert "client_id=test_client_id" in body["authorize_url"]
    assert f"state={body['state']}" in body["authorize_url"]

    db = SessionLocal()
    try:
        stored = db.query(SumupOAuthState).filter(SumupOAuthState.state == body["state"]).first()
        assert stored is not None
        assert stored.organisation_id == org_id
        assert not oauth_state_expired(stored.expires_at)
    finally:
        db.close()


def test_authorize_requires_client_id(monkeypatch):
    org_id = _seed_tenant()
    monkeypatch.delenv("SUMUP_CLIENT_ID", raising=False)
    monkeypatch.setenv("SUMUP_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SUMUP_REDIRECT_URI", "https://admin.test/sumup/oauth/callback")

    r = client.post(
        f"/sumup/organisations/{org_id}/authorize",
        headers=_auth_headers(),
    )
    assert r.status_code == 503, r.text


def test_connect_member_forbidden():
    org_id = _seed_tenant()
    r = client.get(
        f"/sumup/organisations/{org_id}/status",
        headers=_member_headers(org_id),
    )
    assert r.status_code == 403, r.text


def _seed_oauth_state(org_id: int, state: str = "oauth-state-123") -> str:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email.like("sumup-connect-%@test.local"))
            .order_by(User.id.desc())
            .first()
        )
        db.add(
            SumupOAuthState(
                state=state,
                organisation_id=org_id,
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        db.commit()
    finally:
        db.close()
    return state


def _sumup_oauth_env(monkeypatch) -> None:
    monkeypatch.setenv("SUMUP_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("SUMUP_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SUMUP_REDIRECT_URI", "https://admin.test/sumup/oauth/callback")
    monkeypatch.setenv("SUMUP_FRONTEND_RETURN_URL", "https://admin.test/sumup-devices")


@patch("app.routers.sumup_connect.sumup_client.exchange_code_for_tokens")
@patch("app.routers.sumup_connect.sumup_client.get_merchant_profile")
def test_oauth_callback_exchanges_code_and_connects(mock_profile, mock_exchange, monkeypatch):
    org_id = _seed_tenant()
    _sumup_oauth_env(monkeypatch)
    state = _seed_oauth_state(org_id)

    mock_exchange.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_profile.return_value = {"merchant_code": "MK10CL2A"}

    r = client.get(
        f"/sumup/oauth/callback?code=auth-code-xyz&state={state}",
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    assert r.headers["location"] == "https://admin.test/sumup-devices?connected=1"

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        assert org.sumup_merchant_code == "MK10CL2A"
        assert org.sumup_access_token == "new_access"
        assert org.sumup_refresh_token == "new_refresh"
        assert org.sumup_connected_at is not None
        assert db.query(SumupOAuthState).filter(SumupOAuthState.state == state).first() is None
    finally:
        db.close()


def test_oauth_callback_redirects_sumup_error_to_frontend(monkeypatch):
    _seed_tenant()
    _sumup_oauth_env(monkeypatch)
    r = client.get(
        "/sumup/oauth/callback?error=access_denied&error_description=User%20denied&state=x",
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    assert r.headers["location"].startswith("https://admin.test/sumup-devices?")
    assert "error=" in r.headers["location"]
    assert "access_denied" in r.headers["location"] or "User" in r.headers["location"]


def test_oauth_callback_redirects_invalid_state_to_frontend(monkeypatch):
    _seed_tenant()
    _sumup_oauth_env(monkeypatch)
    r = client.get(
        "/sumup/oauth/callback?code=auth-code-xyz&state=unknown-state",
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    assert "error=" in r.headers["location"]
    assert r.headers["location"].startswith("https://admin.test/sumup-devices?")


@patch("app.routers.sumup_connect.sumup_client.exchange_code_for_tokens")
def test_oauth_callback_redirects_token_exchange_failure(mock_exchange, monkeypatch):
    from app.sumup_client import SumupApiError

    org_id = _seed_tenant()
    _sumup_oauth_env(monkeypatch)
    state = _seed_oauth_state(org_id)
    mock_exchange.side_effect = SumupApiError(400, '{"error":"invalid_grant"}')

    r = client.get(
        f"/sumup/oauth/callback?code=auth-code-xyz&state={state}",
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    assert "error=" in r.headers["location"]
    assert r.headers["location"].startswith("https://admin.test/sumup-devices?")


def test_disconnect_clears_connection():
    org_id = _seed_tenant(connected=True)
    r = client.post(
        f"/sumup/organisations/{org_id}/disconnect",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["connected"] is False
    assert body["merchant_code"] is None
    assert body["reader_count"] == 0

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        assert org.sumup_merchant_code is None
        assert org.sumup_access_token is None
        assert org.sumup_refresh_token is None
        assert db.query(SumupReader).filter(SumupReader.organisation_id == org_id).count() == 0
    finally:
        db.close()
