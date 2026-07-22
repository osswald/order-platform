"""Cross-tenant user IDOR and organisation user linkage (security #3, #15)."""

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_MEMBER, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _token_for(email: str, password: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _tenant_setup(suffix: str):
    """Two Verleiher; member only in A; org admin for B; org in each tenant."""
    db = SessionLocal()
    try:
        hc_a = HireCompany(name=f"Isolation A {suffix}")
        hc_b = HireCompany(name=f"Isolation B {suffix}")
        db.add_all([hc_a, hc_b])
        db.flush()
        org_a = Organisation(name=f"Org A {suffix}", country_id=country_id_by_code(db, "CH"), hire_company_id=hc_a.id, currency="CHF")
        org_b = Organisation(name=f"Org B {suffix}", country_id=country_id_by_code(db, "CH"), hire_company_id=hc_b.id, currency="CHF")
        db.add_all([org_a, org_b])
        db.flush()
        member_email = f"member-a-{suffix}@tenant.test"
        admin_email = f"admin-b-{suffix}@tenant.test"
        member_a = User(
            email=member_email,
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=None,
        )
        member_a.organisations = [org_a]
        admin_b = User(
            email=admin_email,
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc_b.id,
            is_superuser=False,
        )
        db.add_all([member_a, admin_b])
        db.commit()
        return {
            "member_a_id": member_a.id,
            "org_b_id": org_b.id,
            "admin_b_token": _token_for(admin_email, "secret"),
        }
    finally:
        db.close()


def test_tenant_admin_cannot_update_user_from_other_verleiher():
    ctx = _tenant_setup("update")
    r = client.put(
        f"/users/{ctx['member_a_id']}",
        json={"name": "hacked"},
        headers={"Authorization": f"Bearer {ctx['admin_b_token']}"},
    )
    assert r.status_code == 404


def test_tenant_admin_cannot_delete_user_from_other_verleiher():
    ctx = _tenant_setup("delete")
    r = client.delete(
        f"/users/{ctx['member_a_id']}",
        headers={"Authorization": f"Bearer {ctx['admin_b_token']}"},
    )
    assert r.status_code == 404


def test_tenant_admin_cannot_attach_foreign_user_to_organisation():
    ctx = _tenant_setup("attach")
    r = client.put(
        f"/organisations/{ctx['org_b_id']}",
        json={"user_ids": [ctx["member_a_id"]]},
        headers={"Authorization": f"Bearer {ctx['admin_b_token']}"},
    )
    assert r.status_code == 400
    assert "Verleiher" in r.json()["detail"]["message"]


def test_tenant_admin_can_update_user_in_own_verleiher_via_organisation():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Own Tenant positive")
        db.add(hc)
        db.flush()
        org = Organisation(name="Own Org positive", country_id=country_id_by_code(db, "CH"), hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        member = User(
            email="member-own-positive@tenant.test",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=None,
        )
        member.organisations = [org]
        admin = User(
            email="admin-own-positive@tenant.test",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc.id,
        )
        db.add_all([member, admin])
        db.commit()
        member_id = member.id
    finally:
        db.close()

    token = _token_for("admin-own-positive@tenant.test", "secret")
    r = client.put(
        f"/users/{member_id}",
        json={"name": "updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "updated"


def _home_member_no_orgs_setup(suffix: str):
    """Member with home Verleiher A and no organisations; tenant admin on B."""
    db = SessionLocal()
    try:
        hc_a = HireCompany(name=f"Home A {suffix}")
        hc_b = HireCompany(name=f"Home B {suffix}")
        db.add_all([hc_a, hc_b])
        db.flush()
        org_b = Organisation(
            name=f"Org B home {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc_b.id,
            currency="CHF",
        )
        db.add(org_b)
        db.flush()
        member_email = f"home-member-a-{suffix}@tenant.test"
        admin_email = f"home-admin-b-{suffix}@tenant.test"
        member_a = User(
            email=member_email,
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
            hire_company_id=hc_a.id,
        )
        admin_b = User(
            email=admin_email,
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc_b.id,
        )
        db.add_all([member_a, admin_b])
        db.commit()
        return {
            "member_a_id": member_a.id,
            "org_b_id": org_b.id,
            "admin_b_token": _token_for(admin_email, "secret"),
        }
    finally:
        db.close()


def test_tenant_admin_cannot_update_home_member_of_other_verleiher():
    ctx = _home_member_no_orgs_setup("upd-home")
    r = client.put(
        f"/users/{ctx['member_a_id']}",
        json={"name": "hacked"},
        headers={"Authorization": f"Bearer {ctx['admin_b_token']}"},
    )
    assert r.status_code == 404


def test_tenant_admin_cannot_delete_home_member_of_other_verleiher():
    ctx = _home_member_no_orgs_setup("del-home")
    r = client.delete(
        f"/users/{ctx['member_a_id']}",
        headers={"Authorization": f"Bearer {ctx['admin_b_token']}"},
    )
    assert r.status_code == 404


def test_tenant_admin_cannot_attach_home_member_of_other_verleiher():
    ctx = _home_member_no_orgs_setup("attach-home")
    r = client.put(
        f"/organisations/{ctx['org_b_id']}",
        json={"user_ids": [ctx["member_a_id"]]},
        headers={"Authorization": f"Bearer {ctx['admin_b_token']}"},
    )
    assert r.status_code == 400
    assert "Verleiher" in r.json()["detail"]["message"]
