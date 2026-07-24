"""Password policy for create/change (security backlog F7)."""

from app.database import SessionLocal
from app.models import HireCompany, User
from app.roles import ROLE_PLATFORM_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient


def _seed_tenant_admin() -> None:
    db = SessionLocal()
    try:
        hc = HireCompany(name="Pw Policy HC")
        db.add(hc)
        db.flush()
        db.add(
            User(
                email="pw-policy-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.add(
            User(
                email="pw-policy-user@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_PLATFORM_ADMIN,
                is_superuser=True,
            )
        )
        db.commit()
    finally:
        db.close()


def _auth(client: TestClient, email: str) -> dict[str, str]:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_user_create_rejects_short_password(client: TestClient):
    _seed_tenant_admin()
    r = client.post(
        "/users/",
        headers=_auth(client, "pw-policy-admin@test.local"),
        json={
            "email": "short-pw@example.com",
            "password": "short",
            "role": "member",
            "organisation_ids": [],
        },
    )
    assert r.status_code == 422


def test_user_create_accepts_password_of_min_length(client: TestClient):
    _seed_tenant_admin()
    r = client.post(
        "/users/",
        headers=_auth(client, "pw-policy-admin@test.local"),
        json={
            "email": "long-pw@example.com",
            "password": "longenough1",
            "role": "member",
            "organisation_ids": [],
        },
    )
    assert r.status_code == 201, r.text


def test_change_password_rejects_short_new_password(client: TestClient):
    _seed_tenant_admin()
    r = client.post(
        "/auth/change-password",
        headers=_auth(client, "pw-policy-user@test.local"),
        json={"current_password": "secret", "new_password": "short"},
    )
    assert r.status_code == 422
