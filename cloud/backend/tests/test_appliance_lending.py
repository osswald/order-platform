"""Appliance lending create API: date range, overlap, planned vs active status."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, apply_schema_patches, engine
from app.main import app
from app.models import Appliance, ApplianceLending, HireCompany, Organisation, User
from app.roles import ROLE_ORG_ADMIN
from app.security import get_password_hash

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


def _lending_fixture(suffix: str) -> tuple[int, int, str]:
    suffix = f"{suffix}-{uuid4().hex}"
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Lending Tenant {suffix}")
        db.add(company)
        db.flush()
        org = Organisation(name=f"Lending Org {suffix}", country="CH", hire_company_id=company.id)
        db.add(org)
        db.flush()
        user = User(
            email=f"lending-admin-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORG_ADMIN,
            hire_company_id=company.id,
            is_superuser=False,
        )
        appliance = Appliance(
            hire_company_id=company.id,
            type="server",
            name=f"Lending Server {suffix}",
        )
        db.add_all([user, appliance])
        db.commit()
        return appliance.id, org.id, user.email
    finally:
        db.close()


def test_create_lending_with_duration_days_sets_end_date():
    appliance_id, org_id, email = _lending_fixture("duration")
    token = _token_for(email, "secret")
    today = datetime.now(timezone.utc).date()

    response = client.post(
        f"/appliances/{appliance_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": today.isoformat(),
            "duration_days": 7,
        },
    )
    assert response.status_code == 200, response.text
    lendings = response.json()["lendings"]
    assert len(lendings) == 1
    row = lendings[0]
    assert row["start_date"] == today.isoformat()
    assert row["end_date"] == (today + timedelta(days=6)).isoformat()
    assert row["segment"] == "current"
    assert response.json()["lending_status"] == "lent"


def test_create_lending_with_end_date_derives_duration():
    appliance_id, org_id, email = _lending_fixture("end-date")
    token = _token_for(email, "secret")
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=6)

    response = client.post(
        f"/appliances/{appliance_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": today.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    row = response.json()["lendings"][0]
    assert row["end_date"] == end.isoformat()


def test_create_lending_rejects_overlap():
    appliance_id, org_id, email = _lending_fixture("overlap")
    token = _token_for(email, "secret")
    today = datetime.now(timezone.utc).date()

    first = client.post(
        f"/appliances/{appliance_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": today.isoformat(),
            "duration_days": 7,
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/appliances/{appliance_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": (today + timedelta(days=3)).isoformat(),
            "duration_days": 5,
        },
    )
    assert second.status_code == 400
    assert "overlap" in second.json()["detail"].lower()


def test_planned_lending_not_marked_lent_until_start():
    appliance_id, org_id, email = _lending_fixture("planned")
    token = _token_for(email, "secret")
    today = datetime.now(timezone.utc).date()
    future_start = today + timedelta(days=7)

    response = client.post(
        f"/appliances/{appliance_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": future_start.isoformat(),
            "duration_days": 3,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lending_status"] == "available"
    assert body["current_lending"] is None
    assert body["lendings"][0]["segment"] == "future"
