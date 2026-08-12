"""Appliance lending create now goes through rentals; overlap and planned vs active status."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import Appliance, HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


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
        org = Organisation(name=f"Lending Org {suffix}", country_id=country_id_by_code(db, "CH"), hire_company_id=company.id, currency="CHF")
        db.add(org)
        db.flush()
        user = User(
            email=f"lending-admin-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
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


def _create_rental(token: str, org_id: int, appliance_id: int, start, end):
    return client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "appliance_ids": [appliance_id],
        },
    )


def test_create_lending_with_duration_days_sets_end_date():
    appliance_id, org_id, email = _lending_fixture("duration")
    token = _token_for(email, "secret")
    today = datetime.now(UTC).date()
    end = today + timedelta(days=6)

    response = _create_rental(token, org_id, appliance_id, today, end)
    assert response.status_code == 201, response.text
    row = response.json()["lendings"][0]
    assert row["start_date"] == today.isoformat()
    assert row["end_date"] == end.isoformat()
    assert row["segment"] == "current"

    appliance = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    assert appliance.json()["lending_status"] == "lent"
    hist = appliance.json()["lendings"][0]
    assert hist["rental_id"] is not None
    assert hist["rental_display_name"]

    org_rows = client.get(
        f"/organisations/{org_id}/appliance-lendings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert org_rows.status_code == 200, org_rows.text
    current = org_rows.json()["current"]
    assert len(current) == 1
    assert current[0]["rental_id"] == hist["rental_id"]
    assert current[0]["rental_display_name"] == hist["rental_display_name"]


def test_create_lending_with_end_date_derives_duration():
    appliance_id, org_id, email = _lending_fixture("end-date")
    token = _token_for(email, "secret")
    today = datetime.now(UTC).date()
    end = today + timedelta(days=6)

    response = _create_rental(token, org_id, appliance_id, today, end)
    assert response.status_code == 201, response.text
    assert response.json()["lendings"][0]["end_date"] == end.isoformat()


def test_create_lending_rejects_overlap():
    appliance_id, org_id, email = _lending_fixture("overlap")
    token = _token_for(email, "secret")
    today = datetime.now(UTC).date()

    first = _create_rental(token, org_id, appliance_id, today, today + timedelta(days=6))
    assert first.status_code == 201, first.text

    second = _create_rental(token, org_id, appliance_id, today + timedelta(days=3), today + timedelta(days=7))
    assert second.status_code == 400
    assert second.json()["detail"]["code"] == "lending_overlap"


def test_planned_lending_not_marked_lent_until_start():
    appliance_id, org_id, email = _lending_fixture("planned")
    token = _token_for(email, "secret")
    today = datetime.now(UTC).date()
    future_start = today + timedelta(days=7)

    response = _create_rental(token, org_id, appliance_id, future_start, future_start + timedelta(days=2))
    assert response.status_code == 201, response.text
    assert response.json()["lendings"][0]["segment"] == "future"
    appliance = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    body = appliance.json()
    assert body["lending_status"] == "available"
    assert body["current_lending"] is None
    assert body["lendings"][0]["segment"] == "future"


def test_legacy_appliance_lending_post_requires_rental():
    appliance_id, org_id, email = _lending_fixture("legacy-post")
    token = _token_for(email, "secret")
    today = datetime.now(UTC).date()
    response = client.post(
        f"/appliances/{appliance_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": today.isoformat(),
            "duration_days": 7,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "rental_required"
