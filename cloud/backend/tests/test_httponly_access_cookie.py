"""HttpOnly access cookie + cookie CSRF Origin checks (security #16)."""

from __future__ import annotations

from app.database import SessionLocal
from app.models import User
from app.roles import ROLE_PLATFORM_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient


def _create_user(email: str, password: str) -> None:
    db = SessionLocal()
    try:
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                role=ROLE_PLATFORM_ADMIN,
                is_superuser=True,
                token_version=0,
            )
        )
        db.commit()
    finally:
        db.close()


def _set_cookies_from(response, client: TestClient) -> None:
    client.cookies.clear()
    client.cookies.update({name: value for name, value in response.cookies.items()})


def test_login_sets_httponly_access_and_refresh_cookies(client: TestClient):
    _create_user("cookie-login@example.com", "secret")
    r = client.post("/auth/token", data={"username": "cookie-login@example.com", "password": "secret"})
    assert r.status_code == 200
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies
    set_cookie_values = []
    if hasattr(r.headers, "get_list"):
        set_cookie_values = r.headers.get_list("set-cookie")
    else:
        set_cookie_values = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
    joined = "\n".join(set_cookie_values).lower()
    assert "httponly" in joined
    assert "access_token=" in joined
    assert "refresh_token=" in joined


def test_me_accepts_access_cookie_without_bearer(client: TestClient):
    _create_user("cookie-me@example.com", "secret")
    login = client.post("/auth/token", data={"username": "cookie-me@example.com", "password": "secret"})
    assert login.status_code == 200
    _set_cookies_from(login, client)
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "cookie-me@example.com"


def test_cookie_auth_mutation_rejected_without_allowed_origin(client: TestClient, monkeypatch):
    import app.csrf as csrf_mod

    monkeypatch.setattr(csrf_mod, "allowed_origins", ["http://localhost:5173"])
    _create_user("cookie-csrf@example.com", "secret")
    login = client.post("/auth/token", data={"username": "cookie-csrf@example.com", "password": "secret"})
    _set_cookies_from(login, client)
    r = client.patch("/auth/me", json={"theme_preference": "dark"})
    assert r.status_code == 403


def test_cookie_auth_mutation_allowed_with_origin(client: TestClient, monkeypatch):
    import app.csrf as csrf_mod

    monkeypatch.setattr(csrf_mod, "allowed_origins", ["http://localhost:5173"])
    _create_user("cookie-ok@example.com", "secret")
    login = client.post("/auth/token", data={"username": "cookie-ok@example.com", "password": "secret"})
    _set_cookies_from(login, client)
    r = client.patch(
        "/auth/me",
        json={"theme_preference": "dark"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 200
    assert r.json()["theme_preference"] == "dark"


def test_bearer_mutation_skips_origin_check(client: TestClient, monkeypatch):
    import app.csrf as csrf_mod

    monkeypatch.setattr(csrf_mod, "allowed_origins", ["http://localhost:5173"])
    _create_user("bearer-skip@example.com", "secret")
    login = client.post("/auth/token", data={"username": "bearer-skip@example.com", "password": "secret"})
    token = login.json()["access_token"]
    client.cookies.clear()
    r = client.patch(
        "/auth/me",
        json={"theme_preference": "light"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_production_forces_secure_cookie_flag(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("REFRESH_COOKIE_SECURE", raising=False)
    from app.routers import auth as auth_mod

    params = auth_mod._session_cookie_params(max_age=60)
    assert params["secure"] is True
