"""Countries reference API."""

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, TaxCode, User
from app.roles import ROLE_MEMBER, ROLE_PLATFORM_ADMIN
from app.security import get_password_hash
from tests.helpers import country_id_by_code

client = TestClient(app)


def _token(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _setup_users():
    db = SessionLocal()
    try:
        member = User(
            email="countries-member@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        platform = User(
            email="countries-platform@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
        )
        db.add_all([member, platform])
        db.commit()
    finally:
        db.close()


def test_list_countries_requires_auth():
    r = client.get("/countries/")
    assert r.status_code == 401


def test_list_countries_seeded():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('countries-member@test.local')}"}
    r = client.get("/countries/", headers=headers)
    assert r.status_code == 200, r.text
    codes = {row["code"] for row in r.json()}
    assert "CH" in codes
    assert "DE" in codes


def test_platform_admin_can_create_country():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('countries-platform@test.local')}"}
    created = client.post(
        "/countries/",
        headers=headers,
        json={"code": "LU", "name": "Luxemburg"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["code"] == "LU"


def test_member_cannot_create_country():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('countries-member@test.local')}"}
    created = client.post(
        "/countries/",
        headers=headers,
        json={"code": "LU", "name": "Luxemburg 2"},
    )
    assert created.status_code == 403


def test_delete_unused_country():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('countries-platform@test.local')}"}
    created = client.post(
        "/countries/",
        headers=headers,
        json={"code": "LU", "name": "Luxemburg Delete"},
    )
    assert created.status_code == 201, created.text
    country_id = created.json()["id"]
    deleted = client.delete(f"/countries/{country_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text


def test_delete_country_in_use_by_organisation():
    _setup_users()
    db = SessionLocal()
    try:
        ch_id = country_id_by_code(db, "CH")
        hc = HireCompany(name="Country Use HC")
        db.add(hc)
        db.flush()
        db.add(
            Organisation(
                name="Country Use Org",
                country_id=ch_id,
                hire_company_id=hc.id,
                currency="CHF",
            )
        )
        db.commit()
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {_token('countries-platform@test.local')}"}
    deleted = client.delete(f"/countries/{ch_id}", headers=headers)
    assert deleted.status_code == 400


def test_delete_country_in_use_by_tax_code():
    _setup_users()
    db = SessionLocal()
    try:
        ch_id = country_id_by_code(db, "CH")
        tax_code = db.query(TaxCode).filter(TaxCode.country_id == ch_id).first()
        assert tax_code is not None
        tax_country_id = ch_id
        db.close()
    except Exception:
        db.close()
        raise

    headers = {"Authorization": f"Bearer {_token('countries-platform@test.local')}"}
    deleted = client.delete(f"/countries/{tax_country_id}", headers=headers)
    assert deleted.status_code == 400
