"""User theme preference on GET/PATCH /auth/me."""

from app.database import SessionLocal
from app.models import User
from app.roles import ROLE_PLATFORM_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient


def _create_user(email: str, password: str, theme_preference: str = "system") -> None:
    db = SessionLocal()
    try:
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                role=ROLE_PLATFORM_ADMIN,
                is_superuser=True,
                token_version=0,
                theme_preference=theme_preference,
            )
        )
        db.commit()
    finally:
        db.close()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_get_me_returns_default_theme_preference(client: TestClient):
    _create_user("theme-default@example.com", "secret")
    token = _login(client, "theme-default@example.com", "secret")

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["theme_preference"] == "system"


def test_get_me_returns_stored_theme_preference(client: TestClient):
    _create_user("theme-dark@example.com", "secret", theme_preference="dark")
    token = _login(client, "theme-dark@example.com", "secret")

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["theme_preference"] == "dark"


def test_patch_me_updates_theme_preference(client: TestClient):
    _create_user("theme-patch@example.com", "secret")
    token = _login(client, "theme-patch@example.com", "secret")

    r = client.patch(
        "/auth/me",
        json={"theme_preference": "light"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["theme_preference"] == "light"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "theme-patch@example.com").first()
        assert user is not None
        assert user.theme_preference == "light"
    finally:
        db.close()


def test_patch_me_rejects_invalid_theme_preference(client: TestClient):
    _create_user("theme-invalid@example.com", "secret")
    token = _login(client, "theme-invalid@example.com", "secret")

    r = client.patch(
        "/auth/me",
        json={"theme_preference": "neon"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
