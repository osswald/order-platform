"""Multi-tenant hire company isolation."""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN
from app.security import get_password_hash

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    Base.metadata.create_all(bind=engine)
    yield


def _token_for(email: str, password: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_default_hire_company_backfill_name():
    db = SessionLocal()
    try:
        vendiqo = db.query(HireCompany).filter(HireCompany.name == "Vendiqo").first()
        assert vendiqo is not None
    finally:
        db.close()


def test_org_admin_cannot_access_other_tenant_organisation():
    db = SessionLocal()
    try:
        hc_a = HireCompany(name="Tenant A")
        hc_b = HireCompany(name="Tenant B")
        db.add_all([hc_a, hc_b])
        db.flush()
        org_b = Organisation(
            name="Org B",
            country="CH",
            hire_company_id=hc_b.id,
        )
        db.add(org_b)
        admin_a = User(
            email="orgadmin-a@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORG_ADMIN,
            hire_company_id=hc_a.id,
            is_superuser=False,
        )
        db.add(admin_a)
        db.commit()
        org_b_id = org_b.id
    finally:
        db.close()

    token = _token_for("orgadmin-a@test.local", "secret")
    r = client.get(
        f"/organisations/{org_b_id}/appliance-lendings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_platform_admin_lists_hire_companies():
    db = SessionLocal()
    try:
        plat = User(
            email="plat-admin@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
        )
        db.add(plat)
        db.commit()
    finally:
        db.close()

    token = _token_for("plat-admin@test.local", "secret")
    r = client.get("/hire-companies/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
