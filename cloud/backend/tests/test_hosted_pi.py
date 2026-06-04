"""Hosted Cloud Pi API and provisioning rules."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Event, HireCompany, HostedPiInstance, Organisation, User
from app.roles import ROLE_ORG_ADMIN
from app.security import get_password_hash

client = TestClient(app)


def _utc_now():
    return datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def _mock_manager(monkeypatch):
    async def _provision(**kwargs):
        return None

    async def _destroy(slug):
        return None

    monkeypatch.setattr("app.hosted_pi_service.provision_instance", _provision)
    monkeypatch.setattr("app.hosted_pi_service.destroy_instance", _destroy)


def _setup_org_admin() -> tuple[int, str]:
    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Hosted HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(name=f"Hosted Org {suffix}", country="CH", hire_company_id=hc.id)
        db.add(org)
        db.flush()
        db.add(
            User(
                email=f"hosted-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_ORG_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id, f"hosted-{suffix}@test.local"
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _create_config_event(org_id: int, headers: dict) -> int:
    now = _utc_now()
    created = client.post(
        "/events/",
        headers=headers,
        json={
            "name": "Config Event",
            "status": "config",
            "start": (now + timedelta(days=30)).isoformat(),
            "end": (now + timedelta(days=31)).isoformat(),
            "currency": "CHF",
            "organisation_id": org_id,
            "payment_mode": "pay_later",
            "payment_types": ["cash"],
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["id"]


def test_start_hosted_pi_for_config_event():
    org_id, email = _setup_org_admin()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    event_id = _create_config_event(org_id, headers)

    response = client.post(f"/events/{event_id}/hosted-pi", headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "running"
    assert body["url"].startswith("https://")
    assert body["url"].endswith(".demo.vendiqo.ch")


def test_rejects_non_config_event():
    org_id, email = _setup_org_admin()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    event_id = _create_config_event(org_id, headers)
    updated = client.put(f"/events/{event_id}", headers=headers, json={"status": "test"})
    assert updated.status_code == 200

    response = client.post(f"/events/{event_id}/hosted-pi", headers=headers)
    assert response.status_code == 422


def test_global_max_five_instances():
    org_id, email = _setup_org_admin()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    for i in range(5):
        event_id = _create_config_event(org_id, headers)
        response = client.post(f"/events/{event_id}/hosted-pi", headers=headers)
        assert response.status_code == 201, response.text

    event_id = _create_config_event(org_id, headers)
    response = client.post(f"/events/{event_id}/hosted-pi", headers=headers)
    assert response.status_code == 429


def test_delete_hosted_pi():
    org_id, email = _setup_org_admin()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    event_id = _create_config_event(org_id, headers)
    started = client.post(f"/events/{event_id}/hosted-pi", headers=headers)
    assert started.status_code == 201

    deleted = client.delete(f"/events/{event_id}/hosted-pi", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "stopped"

    db = SessionLocal()
    try:
        row = db.query(HostedPiInstance).filter(HostedPiInstance.event_id == event_id).first()
        assert row is not None
        assert row.status == "stopped"
    finally:
        db.close()
