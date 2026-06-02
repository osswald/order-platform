"""Headless Raspberry Pi pairing flow for server appliances."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, apply_schema_patches, engine
from app.main import app
from app.models import Appliance, ApplianceEdgeCredential, ApplianceLending, AppliancePairingSession, HireCompany, Organisation, User
from app.roles import ROLE_ORG_ADMIN
from app.security import get_password_hash, verify_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    yield


def _token_for(email: str, password: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _server_appliance_fixture(suffix: str) -> tuple[int, str]:
    suffix = f"{suffix}-{uuid4().hex}"
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Pairing Tenant {suffix}")
        db.add(company)
        db.flush()
        org = Organisation(name=f"Pairing Org {suffix}", country="CH", hire_company_id=company.id)
        db.add(org)
        db.flush()
        user = User(
            email=f"pairing-admin-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORG_ADMIN,
            hire_company_id=company.id,
            is_superuser=False,
        )
        appliance = Appliance(
            hire_company_id=company.id,
            type="server",
            name=f"Pairing Server {suffix}",
        )
        db.add_all([user, appliance])
        db.flush()
        today = datetime.now(timezone.utc).date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today,
                end_date=today,
                returned_at=None,
            )
        )
        db.commit()
        return appliance.id, user.email
    finally:
        db.close()


def test_pairing_code_is_created_and_consumed_once():
    appliance_id, email = _server_appliance_fixture("success")
    token = _token_for(email, "secret")

    created = client.post(
        f"/appliances/{appliance_id}/pairing-sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["pairing_code_display"] == f"{body['pairing_code'][:3]}-{body['pairing_code'][3:]}"
    assert body["setup_url"] == "http://192.168.192.10"

    paired = client.post("/edge/v1/pair", json={"pairing_code": body["pairing_code"], "device_name": "Backup SD"})
    assert paired.status_code == 200, paired.text
    credentials = paired.json()
    assert credentials["appliance_id"] == appliance_id
    assert credentials["edge_client_id"]
    assert credentials["edge_secret"]
    assert credentials["edge_credential_id"]
    assert credentials["installation_label"] == "Backup SD"

    reused = client.post("/edge/v1/pair", json={"pairing_code": body["pairing_code"]})
    assert reused.status_code == 401

    db = SessionLocal()
    try:
        credential = (
            db.query(ApplianceEdgeCredential)
            .filter(ApplianceEdgeCredential.id == credentials["edge_credential_id"])
            .one()
        )
        session = db.query(AppliancePairingSession).filter(AppliancePairingSession.id == body["id"]).one()
        assert credential.appliance_id == appliance_id
        assert credential.edge_client_id == credentials["edge_client_id"]
        assert credential.status == "active"
        assert credential.label == "Backup SD"
        assert verify_password(credentials["edge_secret"], credential.edge_secret_hash)
        assert session.consumed_at is not None
    finally:
        db.close()


def test_pairing_code_must_not_be_expired():
    appliance_id, _email = _server_appliance_fixture("expired")
    db = SessionLocal()
    try:
        session = AppliancePairingSession(
            appliance_id=appliance_id,
            code_hash=get_password_hash("123456"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    paired = client.post("/edge/v1/pair", json={"pairing_code": "123-456"})
    assert paired.status_code == 401



def test_multiple_sd_cards_get_separate_revocable_credentials():
    appliance_id, email = _server_appliance_fixture("multiple")
    token = _token_for(email, "secret")

    first_code = client.post(
        f"/appliances/{appliance_id}/pairing-sessions",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["pairing_code"]
    first = client.post("/edge/v1/pair", json={"pairing_code": first_code, "device_name": "Main SD"})
    assert first.status_code == 200, first.text

    second_code = client.post(
        f"/appliances/{appliance_id}/pairing-sessions",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["pairing_code"]
    second = client.post("/edge/v1/pair", json={"pairing_code": second_code, "device_name": "Backup SD"})
    assert second.status_code == 200, second.text

    first_credentials = first.json()
    second_credentials = second.json()
    assert first_credentials["edge_client_id"] != second_credentials["edge_client_id"]

    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200, detail.text
    installs = detail.json()["edge_credentials"]
    assert {row["label"] for row in installs} >= {"Main SD", "Backup SD"}

    revoked = client.post(
        f"/appliances/{appliance_id}/edge-credentials/{second_credentials['edge_credential_id']}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoked.status_code == 200, revoked.text
    revoked_row = next(row for row in revoked.json()["edge_credentials"] if row["id"] == second_credentials["edge_credential_id"])
    assert revoked_row["status"] == "revoked"

    active_auth = client.get(
        "/edge/v1/bundle",
        headers={
            "X-Edge-Client-Id": first_credentials["edge_client_id"],
            "X-Edge-Secret": first_credentials["edge_secret"],
        },
    )
    assert active_auth.status_code == 200

    revoked_auth = client.get(
        "/edge/v1/bundle",
        headers={
            "X-Edge-Client-Id": second_credentials["edge_client_id"],
            "X-Edge-Secret": second_credentials["edge_secret"],
        },
    )
    assert revoked_auth.status_code == 401


def test_edge_device_can_self_revoke_via_unpair_endpoint():
    appliance_id, email = _server_appliance_fixture("self-revoke")
    token = _token_for(email, "secret")

    pairing_code = client.post(
        f"/appliances/{appliance_id}/pairing-sessions",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["pairing_code"]
    paired = client.post("/edge/v1/pair", json={"pairing_code": pairing_code, "device_name": "Main SD"})
    assert paired.status_code == 200, paired.text
    credentials = paired.json()

    unpair = client.post(
        "/edge/v1/unpair",
        headers={
            "X-Edge-Client-Id": credentials["edge_client_id"],
            "X-Edge-Secret": credentials["edge_secret"],
        },
    )
    assert unpair.status_code == 200, unpair.text
    assert unpair.json()["status"] == "revoked"

    rejected = client.get(
        "/edge/v1/bundle",
        headers={
            "X-Edge-Client-Id": credentials["edge_client_id"],
            "X-Edge-Secret": credentials["edge_secret"],
        },
    )
    assert rejected.status_code == 401
