"""Tax codes reference API."""

from datetime import date

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import User
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
            email="taxcodes-member@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        platform = User(
            email="taxcodes-platform@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
        )
        db.add_all([member, platform])
        db.commit()
    finally:
        db.close()


def test_list_tax_codes_seeded():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('taxcodes-member@test.local')}"}
    r = client.get("/tax-codes/", headers=headers)
    assert r.status_code == 200, r.text
    assert len(r.json()) >= 21


def test_platform_admin_can_create_tax_code():
    _setup_users()
    db = SessionLocal()
    try:
        ch_id = country_id_by_code(db, "CH")
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {_token('taxcodes-platform@test.local')}"}
    created = client.post(
        "/tax-codes/",
        headers=headers,
        json={
            "country_id": ch_id,
            "name": "Test Steuer",
            "rates": [{"rate_percent": 8.1, "valid_from": "2024-01-01"}],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Test Steuer"
    assert len(created.json()["rates"]) == 1


def test_member_cannot_create_tax_code():
    _setup_users()
    db = SessionLocal()
    try:
        ch_id = country_id_by_code(db, "CH")
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {_token('taxcodes-member@test.local')}"}
    created = client.post(
        "/tax-codes/",
        headers=headers,
        json={
            "country_id": ch_id,
            "name": "Blocked",
            "rates": [{"rate_percent": 8.1, "valid_from": "2024-01-01"}],
        },
    )
    assert created.status_code == 403


def test_overlapping_rates_rejected():
    _setup_users()
    db = SessionLocal()
    try:
        de_id = country_id_by_code(db, "DE")
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {_token('taxcodes-platform@test.local')}"}
    created = client.post(
        "/tax-codes/",
        headers=headers,
        json={
            "country_id": de_id,
            "name": "Overlap Test",
            "rates": [
                {"rate_percent": 19.0, "valid_from": "2020-01-01", "valid_to": "2025-12-31"},
                {"rate_percent": 20.0, "valid_from": "2025-06-01"},
            ],
        },
    )
    assert created.status_code == 400


def test_delete_tax_code():
    _setup_users()
    db = SessionLocal()
    try:
        de_id = country_id_by_code(db, "DE")
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {_token('taxcodes-platform@test.local')}"}
    created = client.post(
        "/tax-codes/",
        headers=headers,
        json={
            "country_id": de_id,
            "name": "Delete Me",
            "rates": [{"rate_percent": 5.0, "valid_from": str(date(2020, 1, 1))}],
        },
    )
    assert created.status_code == 201, created.text
    tax_code_id = created.json()["id"]
    deleted = client.delete(f"/tax-codes/{tax_code_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
