"""Unit tests for organisation SumUp credential resolution."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from app import sumup_client
from app.models import Organisation
from app.sumup_tokens import get_valid_access_token


def _org(**kwargs) -> Organisation:
    org = Organisation(name="Token Org", currency="CHF")
    for key, value in kwargs.items():
        setattr(org, key, value)
    return org


def test_get_valid_access_token_returns_static_api_key_without_refresh():
    org = _org(
        sumup_access_token="sup_sk_test_key",
        sumup_refresh_token=None,
        sumup_token_expires_at=None,
    )
    db = MagicMock()
    with patch("app.sumup_tokens.sumup_client.refresh_access_token") as mock_refresh:
        assert get_valid_access_token(db, org) == "sup_sk_test_key"
        mock_refresh.assert_not_called()
    db.commit.assert_not_called()


def test_get_valid_access_token_refreshes_oauth_when_expired():
    org = _org(
        sumup_access_token="old_access",
        sumup_refresh_token="refresh_test",
        sumup_token_expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db = MagicMock()
    with patch(
        "app.sumup_tokens.sumup_client.refresh_access_token",
        return_value={
            "access_token": "new_access",
            "refresh_token": "refresh_test",
            "expires_in": 3600,
        },
    ) as mock_refresh:
        assert get_valid_access_token(db, org) == "new_access"
        mock_refresh.assert_called_once_with("refresh_test")
    assert org.sumup_access_token == "new_access"


def test_get_valid_access_token_uses_unexpired_oauth_access_token():
    org = _org(
        sumup_access_token="still_valid",
        sumup_refresh_token="refresh_test",
        sumup_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db = MagicMock()
    with patch("app.sumup_tokens.sumup_client.refresh_access_token") as mock_refresh:
        assert get_valid_access_token(db, org) == "still_valid"
        mock_refresh.assert_not_called()


def test_get_valid_access_token_raises_when_not_connected():
    org = _org(sumup_access_token=None, sumup_refresh_token=None)
    db = MagicMock()
    with pytest.raises(sumup_client.SumupConfigError):
        get_valid_access_token(db, org)
