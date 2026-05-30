"""Access vs refresh JWT separation (security #2)."""

import pytest
from fastapi.testclient import TestClient
from jose import JWTError

from app.database import Base, engine
from app.main import app
from app.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    Base.metadata.create_all(bind=engine)
    yield


def test_access_token_includes_typ_claim():
    token = create_access_token(data={"sub": "u@example.com"})
    payload = decode_access_token(token)
    assert payload["typ"] == TOKEN_TYPE_ACCESS
    assert payload["sub"] == "u@example.com"


def test_refresh_token_includes_typ_claim():
    token = create_refresh_token(data={"sub": "u@example.com"})
    payload = decode_refresh_token(token)
    assert payload["typ"] == TOKEN_TYPE_REFRESH
    assert payload["sub"] == "u@example.com"


def test_refresh_token_rejected_as_access_token():
    refresh = create_refresh_token(data={"sub": "u@example.com"})
    with pytest.raises(JWTError):
        decode_access_token(refresh)


def test_access_token_rejected_as_refresh_token():
    access = create_access_token(data={"sub": "u@example.com"})
    with pytest.raises(JWTError):
        decode_refresh_token(access)


def test_refresh_token_cannot_authenticate_bearer_requests():
    refresh_token = create_refresh_token(data={"sub": "any@example.com"})
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert me.status_code == 401
