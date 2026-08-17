"""Unit tests for SumUp client helpers."""

from unittest.mock import patch

from app.sumup_client import (
    SumupApiError,
    SumupConfigError,
    build_authorize_url,
    get_merchant_profile,
    get_merchant_profile_for_code,
    list_merchant_memberships,
    list_readers,
    merchant_display_name,
    merchant_sandbox_flag,
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


def test_merchant_display_name_prefers_business_profile():
    name = merchant_display_name(
        me_payload={"merchant_profile": {"company_name": "Me Name"}},
        merchant={
            "alias": "Alias Cafe",
            "business_profile": {"name": "Example Coffee"},
            "company": {"name": "Legal GmbH"},
        },
    )
    assert name == "Alias Cafe"


def test_merchant_display_name_falls_back_to_me_profile():
    name = merchant_display_name(
        me_payload={"merchant_profile": {"company_name": "Me Name"}},
        merchant=None,
    )
    assert name == "Me Name"


def test_merchant_sandbox_flag():
    assert merchant_sandbox_flag({"sandbox": True}) is True
    assert merchant_sandbox_flag({"sandbox": False}) is False
    assert merchant_sandbox_flag({}) is None
    assert merchant_sandbox_flag(None) is None
    # SumUp often omits the field on live merchants after a successful Merchant fetch.
    assert merchant_sandbox_flag({}, fetched=True) is False
    assert merchant_sandbox_flag({"merchant_code": "X"}, fetched=True) is False
    assert merchant_sandbox_flag(None, fetched=True) is None


@patch("app.sumup_client.request_json")
def test_get_merchant_profile_includes_sandbox_and_name(mock_request):
    mock_request.side_effect = [
        {"merchant_profile": {"merchant_code": "MKSANDBOX", "company_name": "Old"}},
        {
            "merchant_code": "MKSANDBOX",
            "sandbox": True,
            "alias": "Sandbox Cafe",
            "country": "CH",
        },
    ]
    profile = get_merchant_profile("sup_sk_test")
    assert profile["merchant_code"] == "MKSANDBOX"
    assert profile["merchant_name"] == "Sandbox Cafe"
    assert profile["sandbox"] is True
    assert profile["country"] == "CH"
    assert mock_request.call_count == 2
    assert mock_request.call_args_list[1].args[1].endswith("/v1/merchants/MKSANDBOX")


@patch("app.sumup_client.request_json")
def test_get_merchant_profile_treats_omitted_sandbox_as_live(mock_request):
    mock_request.side_effect = [
        {"merchant_profile": {"merchant_code": "MKLIVE", "company_name": "Live GmbH"}},
        {
            "merchant_code": "MKLIVE",
            "company": {"name": "Live GmbH"},
            "country": "CH",
        },
    ]
    profile = get_merchant_profile("sup_sk_live")
    assert profile["sandbox"] is False
    assert profile["merchant_name"] == "Live GmbH"


@patch("app.sumup_client.request_json")
def test_get_merchant_profile_survives_merchant_lookup_failure(mock_request):
    mock_request.side_effect = [
        {"merchant_profile": {"merchant_code": "MKLIVE", "company_name": "Live GmbH"}},
        SumupApiError(404, "not found"),
    ]
    profile = get_merchant_profile("sup_sk_live")
    assert profile["merchant_code"] == "MKLIVE"
    assert profile["merchant_name"] == "Live GmbH"
    assert profile["sandbox"] is None


@patch("app.sumup_client.request_json")
def test_list_merchant_memberships_parses_test_accounts(mock_request):
    mock_request.return_value = {
        "items": [
            {
                "status": "accepted",
                "type": "merchant",
                "resource_id": "MCLIVE",
                "resource": {
                    "id": "MCLIVE",
                    "name": "Live Cafe",
                    "type": "merchant",
                    "attributes": {
                        "merchant_code": "MCLIVE",
                        "merchant_country": "CH",
                    },
                },
            },
            {
                "status": "accepted",
                "type": "merchant",
                "resource_id": "MCSAND",
                "resource": {
                    "id": "MCSAND",
                    "name": "Sandbox Cafe",
                    "type": "merchant",
                    "attributes": {
                        "merchant_code": "MCSAND",
                        "merchant_country": "CH",
                        "is_test_account": True,
                    },
                },
            },
            {
                "status": "pending",
                "type": "merchant",
                "resource_id": "MCPEND",
                "resource": {
                    "id": "MCPEND",
                    "name": "Pending",
                    "type": "merchant",
                    "attributes": {"merchant_code": "MCPEND"},
                },
            },
        ]
    }
    members = list_merchant_memberships("sup_sk_test")
    assert [m["merchant_code"] for m in members] == ["MCLIVE", "MCSAND"]
    assert members[0]["sandbox"] is False
    assert members[1]["sandbox"] is True
    assert members[1]["merchant_name"] == "Sandbox Cafe"
    assert members[1]["country"] == "CH"


@patch("app.sumup_client.request_json")
def test_list_readers_returns_items(mock_request):
    mock_request.return_value = {
        "items": [{"id": "rdr_3MSAFM23CK82VSTT4BN6RWSQ65", "name": "Bar", "status": "paired"}]
    }
    items = list_readers("token", "MK10CL2A")
    assert len(items) == 1
    assert items[0]["id"] == "rdr_3MSAFM23CK82VSTT4BN6RWSQ65"


@patch("app.sumup_client.request_json")
def test_list_readers_empty_items_is_well_formed(mock_request):
    mock_request.return_value = {"items": []}
    assert list_readers("token", "MK10CL2A") == []


@patch("app.sumup_client.request_json")
def test_list_readers_raises_when_items_missing(mock_request):
    mock_request.return_value = {"data": []}
    try:
        list_readers("token", "MK10CL2A")
        raise AssertionError("expected SumupApiError")
    except SumupApiError as exc:
        assert exc.status_code == 502


@patch("app.sumup_client.request_json")
def test_list_readers_raises_when_items_not_a_list(mock_request):
    mock_request.return_value = {"items": None}
    try:
        list_readers("token", "MK10CL2A")
        raise AssertionError("expected SumupApiError")
    except SumupApiError as exc:
        assert exc.status_code == 502


@patch("app.sumup_client.request_json")
def test_get_transaction_by_client_transaction_id(mock_request):
    from app.sumup_client import get_transaction

    mock_request.return_value = {"id": "txn", "transaction_code": "ABC"}
    out = get_transaction("tok", "MK10CL2A", client_transaction_id="ctx-1")
    assert out["transaction_code"] == "ABC"
    url = mock_request.call_args.args[1]
    assert "/v2.1/merchants/MK10CL2A/transactions?" in url
    assert "client_transaction_id=ctx-1" in url


@patch("app.sumup_client.request_json")
def test_get_merchant_profile_for_code(mock_request):
    mock_request.return_value = {
        "merchant_code": "MCSAND",
        "sandbox": True,
        "alias": "Sandbox Cafe",
        "country": "CH",
    }
    profile = get_merchant_profile_for_code("sup_sk_test", "MCSAND")
    assert profile["merchant_code"] == "MCSAND"
    assert profile["merchant_name"] == "Sandbox Cafe"
    assert profile["sandbox"] is True
    assert profile["country"] == "CH"
    assert mock_request.call_args.args[1].endswith("/v1/merchants/MCSAND")
