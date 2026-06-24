"""Waiters HTTP API."""

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from tests.helpers import country_id_by_code

client = TestClient(app)


def _setup_tenant() -> tuple[int, str]:
    db = SessionLocal()
    try:
        hc = HireCompany(name="Waiters HC")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Waiters Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="waiters-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id, "waiters-admin@test.local"
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_list_and_create_waiter():
    org_id, email = _setup_tenant()
    headers = {"Authorization": f"Bearer {_token(email)}"}

    empty = client.get("/waiters/", headers=headers)
    assert empty.status_code == 200, empty.text
    assert empty.json() == []

    created = client.post(
        "/waiters/",
        headers=headers,
        json={"name": "Anna", "pin": "1234", "organisation_id": org_id},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["name"] == "Anna"
    assert body["organisation_id"] == org_id

    listed = client.get(f"/waiters/?organisation_id={org_id}", headers=headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    assert listed.json()[0]["name"] == "Anna"
