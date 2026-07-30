"""Persist Pi backend app version from edge request headers onto SD-card credentials."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _token_for(email: str, password: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _edge_fixture() -> tuple[int, str, str, str]:
    """Return appliance_id, edge_client_id, edge_secret, admin_email."""
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Version HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Version Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        email = f"version-admin-{suffix}@test.local"
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        appliance = Appliance(
            hire_company_id=hc.id,
            type="server",
            name=f"Version Server {suffix}",
        )
        db.add(appliance)
        db.flush()
        today = datetime.now(UTC).date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today - timedelta(days=1),
                end_date=today + timedelta(days=1),
            )
        )
        client_id = f"client-{suffix}"
        db.add(
            ApplianceEdgeCredential(
                appliance_id=appliance.id,
                edge_client_id=client_id,
                edge_secret_hash=get_password_hash("edge-secret"),
                label="SD",
                status="active",
            )
        )
        db.commit()
        return appliance.id, client_id, "edge-secret", email
    finally:
        db.close()


def test_edge_auth_persists_app_version_and_build_time():
    appliance_id, client_id, secret, email = _edge_fixture()
    response = client.get(
        "/edge/v1/bundle",
        headers={
            "X-Edge-Client-Id": client_id,
            "X-Edge-Secret": secret,
            "X-Edge-App-Version": "1.5.10",
            "X-Edge-App-Build-Time": "202607201045",
        },
    )
    assert response.status_code == 200, response.text

    token = _token_for(email, "secret")
    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200, detail.text
    creds = detail.json()["edge_credentials"]
    assert len(creds) == 1
    assert creds[0]["reported_app_version"] == "1.5.10"
    assert creds[0]["reported_app_build_time"] == "202607201045"
    assert creds[0]["last_seen_at"] is not None


def test_omit_version_headers_leaves_prior_values():
    appliance_id, client_id, secret, email = _edge_fixture()
    assert (
        client.get(
            "/edge/v1/bundle",
            headers={
                "X-Edge-Client-Id": client_id,
                "X-Edge-Secret": secret,
                "X-Edge-App-Version": "1.4.0",
                "X-Edge-App-Build-Time": "202601010000",
            },
        ).status_code
        == 200
    )

    assert (
        client.get(
            "/edge/v1/bundle",
            headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret},
        ).status_code
        == 200
    )

    token = _token_for(email, "secret")
    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    cred = detail.json()["edge_credentials"][0]
    assert cred["reported_app_version"] == "1.4.0"
    assert cred["reported_app_build_time"] == "202601010000"


def test_empty_version_header_leaves_prior_values_and_succeeds():
    appliance_id, client_id, secret, email = _edge_fixture()
    assert (
        client.get(
            "/edge/v1/bundle",
            headers={
                "X-Edge-Client-Id": client_id,
                "X-Edge-Secret": secret,
                "X-Edge-App-Version": "2.0.0",
            },
        ).status_code
        == 200
    )

    assert (
        client.get(
            "/edge/v1/bundle",
            headers={
                "X-Edge-Client-Id": client_id,
                "X-Edge-Secret": secret,
                "X-Edge-App-Version": "   ",
                "X-Edge-App-Build-Time": "ignored",
            },
        ).status_code
        == 200
    )

    token = _token_for(email, "secret")
    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    cred = detail.json()["edge_credentials"][0]
    assert cred["reported_app_version"] == "2.0.0"


def test_oversized_version_header_ignored_without_failing_request():
    appliance_id, client_id, secret, email = _edge_fixture()
    assert (
        client.get(
            "/edge/v1/bundle",
            headers={
                "X-Edge-Client-Id": client_id,
                "X-Edge-Secret": secret,
                "X-Edge-App-Version": "1.0.0",
            },
        ).status_code
        == 200
    )

    oversized = "x" * 128
    assert (
        client.get(
            "/edge/v1/bundle",
            headers={
                "X-Edge-Client-Id": client_id,
                "X-Edge-Secret": secret,
                "X-Edge-App-Version": oversized,
            },
        ).status_code
        == 200
    )

    token = _token_for(email, "secret")
    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.json()["edge_credentials"][0]["reported_app_version"] == "1.0.0"


def test_appliance_detail_exposes_null_version_when_never_reported():
    appliance_id, client_id, secret, email = _edge_fixture()
    token = _token_for(email, "secret")
    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200, detail.text
    cred = detail.json()["edge_credentials"][0]
    assert cred.get("reported_app_version") is None
    assert cred.get("reported_app_build_time") is None
