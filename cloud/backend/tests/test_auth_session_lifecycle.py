"""Session invalidation, refresh rotation, and refresh rate limit (security #9)."""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, apply_schema_patches, engine
from app.main import app
from app.models import User
from app.roles import ROLE_PLATFORM_ADMIN
from app.security import get_password_hash

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    yield


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


def test_logout_invalidates_access_and_refresh():
    _create_user("logout-test@example.com", "secret")
    login = _login("logout-test@example.com", "secret")
    assert login.status_code == 200
    access = login.json()["access_token"]
    cookies = login.cookies

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 200

    logout = client.post("/auth/logout", cookies=cookies)
    assert logout.status_code == 200

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401
    refresh = client.post("/auth/refresh", cookies=cookies)
    assert refresh.status_code == 401


def test_refresh_rotates_and_invalidates_previous_refresh():
    _create_user("rotate-test@example.com", "secret")
    login = _login("rotate-test@example.com", "secret")
    assert login.status_code == 200
    old_cookies = login.cookies

    first = client.post("/auth/refresh", cookies=old_cookies)
    assert first.status_code == 200
    new_cookies = first.cookies

    second_old = client.post("/auth/refresh", cookies=old_cookies)
    assert second_old.status_code == 401

    assert client.post("/auth/refresh", cookies=new_cookies).status_code == 200


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
    cookies = login.cookies

    statuses = []
    for _ in range(35):
        r = client.post("/auth/refresh", cookies=cookies)
        statuses.append(r.status_code)
        if r.status_code == 200:
            cookies = r.cookies

    assert 429 in statuses
