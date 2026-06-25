"""Access vs refresh JWT separation (security #2)."""

import pytest
from app.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from jose import JWTError


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


def test_refresh_token_cannot_authenticate_bearer_requests(client):
    refresh_token = create_refresh_token(data={"sub": "any@example.com"})
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert me.status_code == 401
