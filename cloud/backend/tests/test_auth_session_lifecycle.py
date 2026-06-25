"""Session invalidation, refresh rotation, and refresh rate limit (security #9)."""

from app.database import SessionLocal
from app.main import app
from app.models import User
from app.roles import ROLE_PLATFORM_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

client = TestClient(app)


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


def _login(email: str, password: str):
    return client.post("/auth/token", data={"username": email, "password": password})


def _cookie_snapshot(response) -> dict[str, str]:
    return {name: value for name, value in response.cookies.items()}


def _set_client_cookies(cookies: dict[str, str]) -> None:
    client.cookies.clear()
    client.cookies.update(cookies)


def test_logout_invalidates_access_and_refresh():
    _create_user("logout-test@example.com", "secret")
    login = _login("logout-test@example.com", "secret")
    assert login.status_code == 200
    access = login.json()["access_token"]
    _set_client_cookies(_cookie_snapshot(login))

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 200

    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401
    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 401


def test_refresh_rotates_and_invalidates_previous_refresh():
    _create_user("rotate-test@example.com", "secret")
    login = _login("rotate-test@example.com", "secret")
    assert login.status_code == 200
    old_cookies = _cookie_snapshot(login)
    _set_client_cookies(old_cookies)

    first = client.post("/auth/refresh")
    assert first.status_code == 200
    new_cookies = _cookie_snapshot(first)

    stale_client = TestClient(app)
    stale_client.cookies.update(old_cookies)
    second_old = stale_client.post("/auth/refresh")
    assert second_old.status_code == 401

    _set_client_cookies(new_cookies)
    assert client.post("/auth/refresh").status_code == 200


def test_change_password_invalidates_existing_access_token():
    _create_user("pw-change@example.com", "secret")
    login = _login("pw-change@example.com", "secret")
    assert login.status_code == 200
    access = login.json()["access_token"]

    changed = client.post(
        "/auth/change-password",
        json={"current_password": "secret", "new_password": "newsecret"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert changed.status_code == 200

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401


def test_refresh_rate_limit_returns_429():
    _create_user("refresh-limit@example.com", "secret")
    login = _login("refresh-limit@example.com", "secret")
    assert login.status_code == 200
    _set_client_cookies(_cookie_snapshot(login))

    statuses = []
    for _ in range(35):
        r = client.post("/auth/refresh")
        statuses.append(r.status_code)
        if r.status_code == 200:
            _set_client_cookies(_cookie_snapshot(r))

    assert 429 in statuses


def test_login_upgrades_legacy_bcrypt_hash():
    import bcrypt

    legacy_hash = bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode("utf-8")
    db = SessionLocal()
    try:
        db.add(
            User(
                email="legacy-bcrypt@example.com",
                hashed_password=legacy_hash,
                role=ROLE_PLATFORM_ADMIN,
                is_superuser=True,
                token_version=0,
            )
        )
        db.commit()
    finally:
        db.close()

    login = _login("legacy-bcrypt@example.com", "secret")
    assert login.status_code == 200, login.text

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "legacy-bcrypt@example.com").first()
        assert user is not None
        assert user.hashed_password.startswith("$argon2")
    finally:
        db.close()
