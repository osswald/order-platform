"""Four-role RBAC permission matrix."""

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_MEMBER, ROLE_ORGANISATION_ADMIN, ROLE_PLATFORM_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _token(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _setup_tenant_with_org():
    db = SessionLocal()
    try:
        hc = HireCompany(name="RBAC Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(name="RBAC Org", country_id=country_id_by_code(db, "CH"), hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        tenant_admin = User(
            email="tenant-admin@rbac.test",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc.id,
        )
        org_admin = User(
            email="org-admin@rbac.test",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORGANISATION_ADMIN,
        )
        org_admin.organisations = [org]
        member = User(
            email="member@rbac.test",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        member.organisations = [org]
        platform = User(
            email="platform@rbac.test",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
        )
        db.add_all([tenant_admin, org_admin, member, platform])
        db.commit()
        return hc.id, org.id, country_id_by_code(db, "CH")
    finally:
        db.close()


def test_tenant_admin_can_create_and_delete_organisation():
    hc_id, _, ch_id = _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('tenant-admin@rbac.test')}"}
    created = client.post(
        "/organisations/",
        headers=headers,
        json={"name": "New Org", "country_id": ch_id, "currency": "CHF"},
    )
    assert created.status_code == 201, created.text
    org_id = created.json()["id"]
    deleted = client.delete(f"/organisations/{org_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text


def test_organisation_admin_cannot_create_organisation():
    _, _, ch_id = _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('org-admin@rbac.test')}"}
    created = client.post(
        "/organisations/",
        headers=headers,
        json={"name": "Blocked Org", "country_id": ch_id, "currency": "CHF"},
    )
    assert created.status_code == 403


def test_organisation_admin_can_update_assigned_organisation():
    _, org_id, _ = _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('org-admin@rbac.test')}"}
    updated = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"name": "Updated Org Name"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated Org Name"


def test_member_cannot_update_organisation():
    _, org_id, _ = _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('member@rbac.test')}"}
    updated = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"name": "Hacked"},
    )
    assert updated.status_code == 403


def test_tenant_admin_can_update_own_hire_company():
    hc_id, _, _ = _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('tenant-admin@rbac.test')}"}
    updated = client.put(
        f"/hire-companies/{hc_id}",
        headers=headers,
        json={"name": "Renamed Tenant"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Renamed Tenant"


def test_tenant_admin_cannot_create_hire_company():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('tenant-admin@rbac.test')}"}
    created = client.post(
        "/hire-companies/",
        headers=headers,
        json={"name": "Extra Tenant"},
    )
    assert created.status_code == 403


def test_organisation_admin_cannot_list_users_without_shared_scope_blocked():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('member@rbac.test')}"}
    listed = client.get("/users/", headers=headers)
    assert listed.status_code == 403


def test_organisation_admin_can_list_users_in_org():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('org-admin@rbac.test')}"}
    listed = client.get("/users/", headers=headers)
    assert listed.status_code == 200, listed.text
    emails = {u["email"] for u in listed.json()}
    assert "member@rbac.test" in emails


def test_platform_admin_lists_hire_companies_with_auth():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('platform@rbac.test')}"}
    listed = client.get("/hire-companies/", headers=headers)
    assert listed.status_code == 200, listed.text


def test_member_can_list_countries():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('member@rbac.test')}"}
    listed = client.get("/countries/", headers=headers)
    assert listed.status_code == 200, listed.text


def test_member_cannot_create_country():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('member@rbac.test')}"}
    created = client.post(
        "/countries/",
        headers=headers,
        json={"code": "XX", "name": "Blocked Land"},
    )
    assert created.status_code == 403


def test_member_can_list_tax_codes():
    _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('member@rbac.test')}"}
    listed = client.get("/tax-codes/", headers=headers)
    assert listed.status_code == 200, listed.text


def test_member_cannot_create_tax_code():
    _, _, ch_id = _setup_tenant_with_org()
    headers = {"Authorization": f"Bearer {_token('member@rbac.test')}"}
    created = client.post(
        "/tax-codes/",
        headers=headers,
        json={
            "country_id": ch_id,
            "name": "Blocked Tax",
            "rates": [{"rate_percent": 8.1, "valid_from": "2024-01-01"}],
        },
    )
    assert created.status_code == 403
