"""SumUp Cloud API client (OAuth, merchant profile, Solo readers, checkouts)."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from fastapi import HTTPException, status

from .i18n.errors import api_error

SUMUP_AUTHORIZE_URL = "https://api.sumup.com/authorize"
SUMUP_TOKEN_URL = "https://api.sumup.com/token"
SUMUP_API_BASE = "https://api.sumup.com"

# Default scopes for Solo Cloud API. Do not include `payments` until SumUp has
# manually activated that restricted scope on the OAuth app — requesting it
# otherwise yields SumUp's "application is misconfigured" authorize error.
# Override with SUMUP_OAUTH_SCOPES (space-separated) when ready.
DEFAULT_OAUTH_SCOPES = (
    "transactions.history",
    "readers.read",
    "readers.write",
    "user.profile_readonly",
)


class SumupConfigError(RuntimeError):
    """Raised when SumUp OAuth is not configured for the cloud backend."""


class SumupApiError(RuntimeError):
    """Raised when a SumUp API request fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"SumUp API error ({status_code}): {detail}")


def normalize_pairing_code(code: str) -> str:
    """Strip spaces/hyphens and uppercase an 8–9 character Solo pairing code."""
    return re.sub(r"[\s\-]+", "", (code or "").strip()).upper()


def sumup_detail_message(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return "SumUp request failed"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:300]
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:300]
        errors = payload.get("errors")
        if isinstance(errors, list):
            for item in errors:
                if isinstance(item, dict):
                    item_detail = item.get("detail") or item.get("message")
                    if isinstance(item_detail, str) and item_detail.strip():
                        return item_detail.strip()[:300]
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:300]
    return text[:300]


def sumup_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SumupConfigError):
        return api_error("validation_failed", status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(exc, SumupApiError):
        detail = sumup_detail_message(exc.detail)
        lowered = detail.lower()
        if exc.status_code == 404 and ("no pairing" in lowered or "pairing" in lowered):
            return api_error("sumup_pairing_code_invalid", status.HTTP_502_BAD_GATEWAY)
        if exc.status_code == 401:
            return api_error("sumup_request_failed", status.HTTP_502_BAD_GATEWAY, detail=detail)
        return api_error("sumup_request_failed", status.HTTP_502_BAD_GATEWAY, detail=detail)
    return api_error("sumup_request_failed", status.HTTP_502_BAD_GATEWAY, detail=str(exc)[:300])


def require_sumup_oauth_config() -> tuple[str, str, str]:
    client_id = (os.getenv("SUMUP_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("SUMUP_CLIENT_SECRET") or "").strip()
    redirect_uri = (os.getenv("SUMUP_REDIRECT_URI") or "").strip()
    if not client_id:
        raise SumupConfigError("SUMUP_CLIENT_ID is not configured")
    if not client_secret:
        raise SumupConfigError("SUMUP_CLIENT_SECRET is not configured")
    if not redirect_uri:
        raise SumupConfigError("SUMUP_REDIRECT_URI is not configured")
    return client_id, client_secret, redirect_uri


def _affiliate_config() -> tuple[str, str]:
    affiliate_key = (os.getenv("SUMUP_AFFILIATE_KEY") or "").strip()
    affiliate_app_id = (os.getenv("SUMUP_AFFILIATE_APP_ID") or "").strip()
    return affiliate_key, affiliate_app_id


def affiliate_key_configured() -> bool:
    """True when Solo checkout can attach platform Affiliate Key metadata."""
    affiliate_key, _ = _affiliate_config()
    return bool(affiliate_key)


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    data: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        response = client.request(method, url, headers=headers, json=json_body, data=data)
    if response.status_code >= 400:
        raise SumupApiError(response.status_code, response.text[:2000])
    if not response.content:
        return {}
    payload = response.json()
    if not isinstance(payload, dict):
        raise SumupApiError(response.status_code, "Unexpected SumUp response shape")
    return payload


def _oauth_scopes(scopes: tuple[str, ...] | None = None) -> tuple[str, ...]:
    if scopes is not None:
        return scopes
    raw = (os.getenv("SUMUP_OAUTH_SCOPES") or "").strip()
    if raw:
        return tuple(part for part in raw.split() if part)
    return DEFAULT_OAUTH_SCOPES


def build_authorize_url(*, state: str, redirect_uri: str, scopes: tuple[str, ...] | None = None) -> str:
    client_id, _, _ = require_sumup_oauth_config()
    scope_list = _oauth_scopes(scopes)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scope_list),
        "state": state,
    }
    # Use %20 for spaces (OAuth examples); quote_plus would emit '+'.
    return f"{SUMUP_AUTHORIZE_URL}?{urlencode(params, quote_via=quote)}"


def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    client_id, client_secret, _ = require_sumup_oauth_config()
    return request_json(
        "POST",
        SUMUP_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    client_id, client_secret, _ = require_sumup_oauth_config()
    return request_json(
        "POST",
        SUMUP_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def merchant_display_name(*, me_payload: dict[str, Any], merchant: dict[str, Any] | None) -> str | None:
    """Pick a human merchant name from Merchant API, then /me fallbacks."""
    if merchant:
        for candidate in (
            merchant.get("alias"),
            (merchant.get("business_profile") or {}).get("name")
            if isinstance(merchant.get("business_profile"), dict)
            else None,
            (merchant.get("company") or {}).get("name") if isinstance(merchant.get("company"), dict) else None,
        ):
            name = _optional_str(candidate)
            if name:
                return name
    merchant_profile = me_payload.get("merchant_profile") if isinstance(me_payload.get("merchant_profile"), dict) else {}
    for candidate in (
        merchant_profile.get("company_name"),
        merchant_profile.get("doing_business_as")
        if isinstance(merchant_profile.get("doing_business_as"), str)
        else None,
    ):
        name = _optional_str(candidate)
        if name:
            return name
    return None


def merchant_sandbox_flag(merchant: dict[str, Any] | None, *, fetched: bool = False) -> bool | None:
    """SumUp Merchant.sandbox: true for test merchants.

    SumUp's OpenAPI documents `sandbox`, but live merchants often omit the field entirely.
    When the Merchant fetch succeeded and the key is absent, treat the account as live.
    """
    if merchant is None:
        return None
    value = merchant.get("sandbox")
    if isinstance(value, bool):
        return value
    if fetched and "sandbox" not in merchant:
        return False
    return None


def merchant_country_code(*, me_payload: dict[str, Any], merchant: dict[str, Any] | None) -> str | None:
    if merchant:
        country = merchant.get("country")
        if isinstance(country, str):
            code = _optional_str(country)
            if code:
                return code.upper()
        if isinstance(country, dict):
            code = _optional_str(country.get("iso_code") or country.get("code"))
            if code:
                return code.upper()
    merchant_profile = me_payload.get("merchant_profile") if isinstance(me_payload.get("merchant_profile"), dict) else {}
    code = _optional_str(merchant_profile.get("country"))
    return code.upper() if code else None


def list_merchant_memberships(access_token: str) -> list[dict[str, Any]]:
    """Merchants accessible with this credential (API keys often span live + sandboxes).

    SumUp ``GET /v0.1/me`` returns only the default merchant; memberships list all
    accepted merchant memberships, including ``is_test_account`` sandboxes.
    """
    payload = request_json(
        "GET",
        f"{SUMUP_API_BASE}/v0.1/memberships",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").lower() != "accepted":
            continue
        resource = item.get("resource") if isinstance(item.get("resource"), dict) else {}
        item_type = str(item.get("type") or resource.get("type") or "").lower()
        if item_type and item_type != "merchant":
            continue
        attrs = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
        merchant_code = _optional_str(
            attrs.get("merchant_code") or resource.get("id") or item.get("resource_id")
        )
        if not merchant_code:
            continue
        is_test = attrs.get("is_test_account")
        sandbox: bool | None
        if isinstance(is_test, bool):
            sandbox = is_test
        else:
            sandbox = False
        country = _optional_str(attrs.get("merchant_country"))
        out.append(
            {
                "merchant_code": merchant_code,
                "merchant_name": _optional_str(resource.get("name")),
                "sandbox": sandbox,
                "country": country.upper() if country else None,
            }
        )
    return out


def get_merchant_profile_for_code(access_token: str, merchant_code: str) -> dict[str, Any]:
    """Load Merchant API details for an explicit merchant code (not ``/me`` default)."""
    code = merchant_code.strip()
    if not code:
        raise SumupApiError(502, "SumUp merchant_code is required")
    merchant: dict[str, Any] | None = None
    try:
        fetched = request_json(
            "GET",
            f"{SUMUP_API_BASE}/v1/merchants/{code}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if isinstance(fetched, dict):
            merchant = fetched
    except SumupApiError:
        merchant = None
    if merchant is None:
        raise SumupApiError(502, f"SumUp merchant {code} is not accessible with this credential")
    return {
        "merchant_code": code,
        "merchant_name": merchant_display_name(me_payload={}, merchant=merchant),
        "sandbox": merchant_sandbox_flag(merchant, fetched=True),
        "country": merchant_country_code(me_payload={}, merchant=merchant),
        "profile": merchant,
    }


def get_merchant_profile(access_token: str) -> dict[str, Any]:
    payload = request_json(
        "GET",
        f"{SUMUP_API_BASE}/v0.1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    merchant_profile = payload.get("merchant_profile") or {}
    merchant_code = merchant_profile.get("merchant_code")
    if not merchant_code:
        raise SumupApiError(502, "SumUp profile response missing merchant_code")
    merchant: dict[str, Any] | None = None
    try:
        fetched = request_json(
            "GET",
            f"{SUMUP_API_BASE}/v1/merchants/{merchant_code}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if isinstance(fetched, dict):
            merchant = fetched
    except SumupApiError:
        merchant = None
    return {
        "merchant_code": merchant_code,
        "merchant_name": merchant_display_name(me_payload=payload, merchant=merchant),
        "sandbox": merchant_sandbox_flag(merchant, fetched=merchant is not None),
        "country": merchant_country_code(me_payload=payload, merchant=merchant),
        "profile": payload,
    }


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _merchant_readers_url(merchant_code: str, reader_id: str | None = None) -> str:
    base = f"{SUMUP_API_BASE}/v0.1/merchants/{merchant_code}/readers"
    if reader_id:
        return f"{base}/{reader_id}"
    return base


def create_reader(access_token: str, merchant_code: str, pairing_code: str, name: str) -> dict[str, Any]:
    code = normalize_pairing_code(pairing_code)
    return request_json(
        "POST",
        _merchant_readers_url(merchant_code),
        headers=_auth_headers(access_token),
        json_body={"pairing_code": code, "name": name},
    )


def list_readers(access_token: str, merchant_code: str) -> list[dict[str, Any]]:
    payload = request_json(
        "GET",
        _merchant_readers_url(merchant_code),
        headers=_auth_headers(access_token),
    )
    items = payload.get("items")
    if not isinstance(items, list):
        raise SumupApiError(502, "SumUp reader list missing items")
    return items


def update_reader(access_token: str, merchant_code: str, reader_id: str, name: str) -> dict[str, Any]:
    return request_json(
        "PATCH",
        _merchant_readers_url(merchant_code, reader_id),
        headers=_auth_headers(access_token),
        json_body={"name": name},
    )


def delete_reader(access_token: str, merchant_code: str, reader_id: str) -> None:
    request_json(
        "DELETE",
        _merchant_readers_url(merchant_code, reader_id),
        headers=_auth_headers(access_token),
    )


def get_reader_status(access_token: str, merchant_code: str, reader_id: str) -> dict[str, Any]:
    """Last-known Solo device status (battery, online, firmware). Firmware 3.3.39.0+."""
    return request_json(
        "GET",
        f"{_merchant_readers_url(merchant_code, reader_id)}/status",
        headers=_auth_headers(access_token),
    )


def create_reader_checkout(
    access_token: str,
    merchant_code: str,
    reader_id: str,
    *,
    amount_cents: int,
    currency: str,
    description: str | None = None,
    foreign_transaction_id: str | None = None,
) -> dict[str, Any]:
    affiliate_key, affiliate_app_id = _affiliate_config()
    body: dict[str, Any] = {
        "total_amount": {
            "currency": currency.upper(),
            "minor_unit": 2,
            "value": amount_cents,
        },
    }
    if description:
        body["description"] = description
    if affiliate_key and affiliate_app_id and foreign_transaction_id:
        body["affiliate"] = {
            "key": affiliate_key,
            "app_id": affiliate_app_id,
            "foreign_transaction_id": foreign_transaction_id,
        }
    return request_json(
        "POST",
        f"{_merchant_readers_url(merchant_code, reader_id)}/checkout",
        headers=_auth_headers(access_token),
        json_body=body,
    )


def terminate_checkout(access_token: str, merchant_code: str, reader_id: str) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{_merchant_readers_url(merchant_code, reader_id)}/terminate",
        headers=_auth_headers(access_token),
    )


def get_reader_checkout(
    access_token: str,
    merchant_code: str,
    reader_id: str,
    checkout_id: str,
) -> dict[str, Any]:
    """Poll Solo Cloud API checkout status (not online ``/v0.1/checkouts/{id}``)."""
    return request_json(
        "GET",
        f"{_merchant_readers_url(merchant_code, reader_id)}/checkout/{checkout_id}",
        headers=_auth_headers(access_token),
    )


def get_checkout(access_token: str, checkout_id: str) -> dict[str, Any]:
    """Online Checkouts API retrieve — not used for Solo reader payments."""
    return request_json(
        "GET",
        f"{SUMUP_API_BASE}/v0.1/checkouts/{checkout_id}",
        headers=_auth_headers(access_token),
    )
