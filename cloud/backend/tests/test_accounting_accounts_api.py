"""Accounting accounts API."""

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import AccountingAccount, HireCompany, Organisation, User
from app.roles import ROLE_MEMBER, ROLE_ORGANISATION_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from tests.helpers import country_id_by_code

client = TestClient(app)


def _token(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _setup_org_with_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "acct-orgadmin@test.local").first()
        if existing:
            org = db.query(Organisation).filter(Organisation.name == "Acct Test Org").first()
            return org.id

        country_id = country_id_by_code(db, "CH")
        hc = HireCompany(name="Acct HC", country_id=country_id)
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Acct Test Org",
            hire_company_id=hc.id,
            country_id=country_id,
            currency="CHF",
            accounts_enabled=True,
        )
        db.add(org)
        db.flush()
        org_admin = User(
            email="acct-orgadmin@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORGANISATION_ADMIN,
        )
        member = User(
            email="acct-member@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        tenant = User(
            email="acct-tenant@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc.id,
        )
        org.users = [org_admin, member]
        db.add_all([org_admin, member, tenant])
        db.commit()
        return org.id
    finally:
        db.close()


def test_org_admin_can_create_accounting_account():
    org_id = _setup_org_with_admin()
    headers = {"Authorization": f"Bearer {_token('acct-orgadmin@test.local')}"}
    created = client.post(
        "/accounting-accounts/",
        headers=headers,
        json={
            "organisation_id": org_id,
            "name": "Erlöse Bar",
            "number": "3000",
            "is_default_for_article_categories": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["number"] == "3000"
    assert body["is_default_for_article_categories"] is True


def test_only_one_category_default_per_org():
    org_id = _setup_org_with_admin()
    headers = {"Authorization": f"Bearer {_token('acct-orgadmin@test.local')}"}
    second = client.post(
        "/accounting-accounts/",
        headers=headers,
        json={
            "organisation_id": org_id,
            "name": "Erlöse TWINT",
            "number": "3001",
            "is_default_for_article_categories": True,
        },
    )
    assert second.status_code == 201, second.text

    db = SessionLocal()
    try:
        defaults = (
            db.query(AccountingAccount)
            .filter(
                AccountingAccount.organisation_id == org_id,
                AccountingAccount.is_default_for_article_categories.is_(True),
            )
            .all()
        )
        assert len(defaults) == 1
        assert defaults[0].number == "3001"
    finally:
        db.close()


def test_member_cannot_create_accounting_account():
    org_id = _setup_org_with_admin()
    headers = {"Authorization": f"Bearer {_token('acct-member@test.local')}"}
    r = client.post(
        "/accounting-accounts/",
        headers=headers,
        json={
            "organisation_id": org_id,
            "name": "Blocked",
            "number": "9999",
        },
    )
    assert r.status_code == 403, r.text


def test_list_accounts_for_org_admin():
    org_id = _setup_org_with_admin()
    headers = {"Authorization": f"Bearer {_token('acct-orgadmin@test.local')}"}
    listed = client.get(f"/accounting-accounts/?organisation_id={org_id}", headers=headers)
    assert listed.status_code == 200, listed.text
    assert isinstance(listed.json(), list)
