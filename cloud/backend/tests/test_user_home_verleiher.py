"""Home Verleiher membership for members and organisation-admins."""

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_MEMBER, ROLE_ORGANISATION_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _token(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _setup(suffix: str):
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Home V {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Home Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        tenant_admin = User(
            email=f"ta-{suffix}@home.example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc.id,
        )
        org_admin = User(
            email=f"oa-{suffix}@home.example.com",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORGANISATION_ADMIN,
            hire_company_id=hc.id,
        )
        org_admin.organisations = [org]
        db.add_all([tenant_admin, org_admin])
        db.commit()
        return {
            "hc_id": hc.id,
            "org_id": org.id,
            "ta_email": tenant_admin.email,
            "oa_email": org_admin.email,
        }
    finally:
        db.close()


def test_create_member_without_orgs_keeps_home_verleiher_and_lists():
    ctx = _setup("member-create")
    headers = {"Authorization": f"Bearer {_token(ctx['ta_email'])}"}
    created = client.post(
        "/users/",
        headers=headers,
        json={
            "email": "new-member@home.example.com",
            "password": "secret",
            "name": "New Member",
            "role": ROLE_MEMBER,
            "organisation_ids": [],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["hire_company_id"] == ctx["hc_id"]
    assert body["organisation_ids"] == []

    listed = client.get("/users/", headers=headers)
    assert listed.status_code == 200, listed.text
    emails = {u["email"] for u in listed.json()}
    assert "new-member@home.example.com" in emails


def test_create_organisation_admin_without_orgs_keeps_home_verleiher_and_lists():
    ctx = _setup("oa-create")
    headers = {"Authorization": f"Bearer {_token(ctx['ta_email'])}"}
    created = client.post(
        "/users/",
        headers=headers,
        json={
            "email": "new-oa@home.example.com",
            "password": "secret",
            "name": "New OA",
            "role": ROLE_ORGANISATION_ADMIN,
            "organisation_ids": [],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["hire_company_id"] == ctx["hc_id"]
    assert body["organisation_ids"] == []

    listed = client.get("/users/", headers=headers)
    assert listed.status_code == 200, listed.text
    emails = {u["email"] for u in listed.json()}
    assert "new-oa@home.example.com" in emails


def test_organisation_admin_create_without_orgs_still_rejected():
    ctx = _setup("oa-actor")
    headers = {"Authorization": f"Bearer {_token(ctx['oa_email'])}"}
    created = client.post(
        "/users/",
        headers=headers,
        json={
            "email": "blocked@home.example.com",
            "password": "secret",
            "role": ROLE_MEMBER,
            "organisation_ids": [],
        },
    )
    assert created.status_code == 400, created.text
    assert created.json()["detail"]["code"] == "organisation_required_for_user"


def test_clear_organisations_keeps_home_verleiher_and_lists():
    ctx = _setup("clear-orgs")
    headers = {"Authorization": f"Bearer {_token(ctx['ta_email'])}"}
    created = client.post(
        "/users/",
        headers=headers,
        json={
            "email": "clear-me@home.example.com",
            "password": "secret",
            "role": ROLE_MEMBER,
            "organisation_ids": [ctx["org_id"]],
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    updated = client.put(
        f"/users/{user_id}",
        headers=headers,
        json={"organisation_ids": []},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["hire_company_id"] == ctx["hc_id"]
    assert updated.json()["organisation_ids"] == []

    listed = client.get("/users/", headers=headers)
    emails = {u["email"] for u in listed.json()}
    assert "clear-me@home.example.com" in emails


def test_demote_tenant_admin_to_member_keeps_home_verleiher():
    ctx = _setup("demote-member")
    headers = {"Authorization": f"Bearer {_token(ctx['ta_email'])}"}
    created = client.post(
        "/users/",
        headers=headers,
        json={
            "email": "demote-member@home.example.com",
            "password": "secret",
            "role": ROLE_TENANT_ADMIN,
            "organisation_ids": [],
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    assert created.json()["hire_company_id"] == ctx["hc_id"]

    updated = client.put(
        f"/users/{user_id}",
        headers=headers,
        json={"role": ROLE_MEMBER, "organisation_ids": []},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["role"] == ROLE_MEMBER
    assert updated.json()["hire_company_id"] == ctx["hc_id"]

    listed = client.get("/users/", headers=headers)
    emails = {u["email"] for u in listed.json()}
    assert "demote-member@home.example.com" in emails


def test_demote_tenant_admin_to_organisation_admin_keeps_home_verleiher():
    ctx = _setup("demote-oa")
    headers = {"Authorization": f"Bearer {_token(ctx['ta_email'])}"}
    created = client.post(
        "/users/",
        headers=headers,
        json={
            "email": "demote-oa@home.example.com",
            "password": "secret",
            "role": ROLE_TENANT_ADMIN,
            "organisation_ids": [],
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    updated = client.put(
        f"/users/{user_id}",
        headers=headers,
        json={"role": ROLE_ORGANISATION_ADMIN, "organisation_ids": []},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["role"] == ROLE_ORGANISATION_ADMIN
    assert updated.json()["hire_company_id"] == ctx["hc_id"]

    listed = client.get("/users/", headers=headers)
    emails = {u["email"] for u in listed.json()}
    assert "demote-oa@home.example.com" in emails
