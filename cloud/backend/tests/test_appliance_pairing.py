"""Headless Raspberry Pi pairing flow for server appliances."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, apply_schema_patches, engine
from app.main import app
from app.models import Appliance, AppliancePairingSession, HireCompany, User
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
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Pairing Tenant {suffix}")
        db.add(company)
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

    paired = client.post("/edge/v1/pair", json={"pairing_code": body["pairing_code"]})
    assert paired.status_code == 200, paired.text
    credentials = paired.json()
    assert credentials["appliance_id"] == appliance_id
    assert credentials["edge_client_id"]
    assert credentials["edge_secret"]

    reused = client.post("/edge/v1/pair", json={"pairing_code": body["pairing_code"]})
    assert reused.status_code == 401

    db = SessionLocal()
    try:
        appliance = db.query(Appliance).filter(Appliance.id == appliance_id).one()
        session = db.query(AppliancePairingSession).filter(AppliancePairingSession.id == body["id"]).one()
        assert appliance.edge_client_id == credentials["edge_client_id"]
        assert verify_password(credentials["edge_secret"], appliance.edge_secret_hash)
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

