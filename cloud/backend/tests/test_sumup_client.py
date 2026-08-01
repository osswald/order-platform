"""Unit tests for SumUp client helpers."""

from app.sumup_client import (
    SumupApiError,
    SumupConfigError,
    build_authorize_url,
    normalize_pairing_code,
    sumup_error,
)
from fastapi import status


def test_normalize_pairing_code_strips_and_uppercases():
    assert normalize_pairing_code(" 4wlf-dsbf ") == "4WLFDSBF"
    assert normalize_pairing_code("abc12def3") == "ABC12DEF3"


def test_build_authorize_url_encodes_scopes_with_percent_twenty(monkeypatch):
    monkeypatch.setenv("SUMUP_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("SUMUP_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SUMUP_REDIRECT_URI", "http://localhost:8000/sumup/oauth/callback")
    url = build_authorize_url(
        state="abc",
        redirect_uri="http://localhost:8000/sumup/oauth/callback",
        scopes=("transactions.history", "user.profile_readonly"),
    )
    assert "scope=transactions.history%20user.profile_readonly" in url
    assert "scope=transactions.history+user.profile_readonly" not in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fsumup%2Foauth%2Fcallback" in url


def test_sumup_error_maps_missing_pairing_code():
    exc = SumupApiError(404, '{"detail":"no pairing for code"}')
    http_exc = sumup_error(exc)
    assert http_exc.status_code == status.HTTP_502_BAD_GATEWAY
    assert http_exc.detail["code"] == "sumup_pairing_code_invalid"


def test_sumup_error_includes_upstream_detail():
    exc = SumupApiError(403, '{"detail":"readers.write required"}')
    http_exc = sumup_error(exc)
    assert http_exc.status_code == status.HTTP_502_BAD_GATEWAY
    assert http_exc.detail["code"] == "sumup_request_failed"
    assert "readers.write required" in http_exc.detail["message"]


def test_sumup_error_config():
    http_exc = sumup_error(SumupConfigError("missing"))
    assert http_exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
