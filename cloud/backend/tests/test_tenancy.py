"""Multi-tenant hire company isolation."""

from app.database import SessionLocal
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_PLATFORM_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash

from tests.helpers import country_id_by_code


def test_default_hire_company_backfill_name():
    db = SessionLocal()
    try:
        vendiqo = db.query(HireCompany).filter(HireCompany.name == "Vendiqo").first()
        assert vendiqo is not None
    finally:
        db.close()


def test_org_admin_cannot_access_other_tenant_organisation(client, auth_token):
    db = SessionLocal()
    try:
        hc_a = HireCompany(name="Tenant A")
        hc_b = HireCompany(name="Tenant B")
        db.add_all([hc_a, hc_b])
        db.flush()
        org_b = Organisation(
            name="Org B",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc_b.id,
            currency="CHF",
        )
        db.add(org_b)
        admin_a = User(
            email="orgadmin-a@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc_a.id,
            is_superuser=False,
        )
        db.add(admin_a)
        db.commit()
        org_b_id = org_b.id
    finally:
        db.close()

    token = auth_token("orgadmin-a@test.local", "secret")
    r = client.get(
        f"/organisations/{org_b_id}/appliance-lendings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_platform_admin_lists_hire_companies(client, auth_token):
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

    token = auth_token("plat-admin@test.local", "secret")
    r = client.get("/hire-companies/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
