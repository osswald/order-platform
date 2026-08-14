"""Pull/push against cloud edge API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx

from .edge_config import read_edge_config
from .version_info import get_app_version, get_build_time


class CloudConfigError(Exception):
    """Raised when required cloud / edge env vars are missing or blank."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing or empty: {', '.join(missing)}")


class CloudRequestError(Exception):
    """Raised when the cloud answered with a non-2xx status."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Cloud request failed ({status_code}): {detail}")


@dataclass(frozen=True)
class ConditionalGetResult:
    """Result of a conditional GET (bundle or snapshot)."""

    not_modified: bool
    data: dict[str, Any] | None
    etag: str | None


def _resolve_config() -> tuple[str, str, str]:
    values = read_edge_config()
    base = (values.get("CLOUD_BASE_URL") or "").strip().rstrip("/")
    cid = (values.get("EDGE_CLIENT_ID") or "").strip()
    secret = (values.get("EDGE_SECRET") or "").strip()
    return base, cid, secret


def _require_config() -> tuple[str, str, str]:
    base, cid, secret = _resolve_config()
    missing = [n for n, v in (("CLOUD_BASE_URL", base), ("EDGE_CLIENT_ID", cid), ("EDGE_SECRET", secret)) if not v]
    if missing:
        raise CloudConfigError(missing)
    return base, cid, secret


def _headers(client_id: str, secret: str) -> dict[str, str]:
    headers = {
        "X-Edge-Client-Id": client_id,
        "X-Edge-Secret": secret,
        "X-Edge-App-Version": get_app_version(),
    }
    build_time = get_build_time()
    if build_time:
        headers["X-Edge-App-Build-Time"] = build_time
    return headers


@asynccontextmanager
async def edge_http_client(
    client: httpx.AsyncClient | None = None,
    *,
    timeout: float = 60.0,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield a shared client when provided; otherwise open a short-lived one."""
    if client is not None:
        yield client
        return
    async with httpx.AsyncClient(timeout=timeout) as owned:
        yield owned


def _response_etag(response: httpx.Response) -> str | None:
    value = response.headers.get("etag") or response.headers.get("ETag")
    return value.strip() if value else None


async def fetch_bundle(
    *,
    client: httpx.AsyncClient | None = None,
    etag: str | None = None,
) -> ConditionalGetResult:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/bundle"
    headers = _headers(cid, secret)
    if etag:
        headers["If-None-Match"] = etag
    async with edge_http_client(client, timeout=60.0) as http:
        r = await http.get(url, headers=headers)
        if r.status_code == 304:
            return ConditionalGetResult(not_modified=True, data=None, etag=_response_etag(r) or etag)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise CloudRequestError(r.status_code, "bundle response was not an object")
        return ConditionalGetResult(not_modified=False, data=data, etag=_response_etag(r))


async def fetch_bundle_manifest(*, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/bundle/manifest"
    async with edge_http_client(client, timeout=30.0) as http:
        r = await http.get(url, headers=_headers(cid, secret))
        r.raise_for_status()
        return r.json()


async def fetch_bundle_chunk(
    *,
    section: str,
    cursor: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/bundle/chunk"
    params: dict[str, str] = {"section": section}
    if cursor:
        params["cursor"] = cursor
    async with edge_http_client(client, timeout=60.0) as http:
        r = await http.get(url, headers=_headers(cid, secret), params=params)
        r.raise_for_status()
        return r.json()


async def submit_order(
    client_order_id: str,
    event_id: int,
    payload: dict[str, Any],
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/orders"
    body = {"client_order_id": client_order_id, "event_id": event_id, "payload": payload}
    async with edge_http_client(client, timeout=60.0) as http:
        r = await http.post(
            url,
            headers={**_headers(cid, secret), "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        return r.json()


async def submit_operational_chunk(
    *,
    chunk_id: str,
    event_id: int,
    entity_type: str,
    payload: dict[str, Any],
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sync/operational/chunk"
    body = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": entity_type,
        "payload": payload,
    }
    async with edge_http_client(client, timeout=60.0) as http:
        r = await http.post(
            url,
            headers={**_headers(cid, secret), "Content-Type": "application/json"},
            json=body,
        )
        if r.status_code == 404:
            client_order_id = str(payload.get("client_order_id") or chunk_id)
            return await submit_order(client_order_id, event_id, payload, client=http)
        r.raise_for_status()
        return r.json()


async def fetch_operational_snapshot(
    *,
    event_id: int | None = None,
    client: httpx.AsyncClient | None = None,
    etag: str | None = None,
) -> ConditionalGetResult:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sync/operational/snapshot"
    params: dict[str, str] = {}
    if event_id is not None:
        params["event_id"] = str(event_id)
    headers = _headers(cid, secret)
    if etag:
        headers["If-None-Match"] = etag
    async with edge_http_client(client, timeout=60.0) as http:
        r = await http.get(url, headers=headers, params=params or None)
        if r.status_code == 304:
            return ConditionalGetResult(not_modified=True, data=None, etag=_response_etag(r) or etag)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise CloudRequestError(r.status_code, "snapshot response was not an object")
        return ConditionalGetResult(not_modified=False, data=data, etag=_response_etag(r))


async def ping_cloud_reachable() -> tuple[bool, str | None]:
    """Return whether the Pi can reach the cloud API."""
    try:
        base, _, _ = _require_config()
    except CloudConfigError:
        return False, "not_configured"
    url = f"{base}/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            if r.is_success:
                return True, None
            return False, f"http_{r.status_code}"
    except Exception as exc:
        return False, str(exc)[:200]


async def create_sumup_checkout(
    *,
    event_id: int,
    amount_cents: int,
    currency: str | None = None,
    reader_id: str,
    client_order_id: str | None = None,
) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sumup/checkout"
    body: dict[str, Any] = {
        "event_id": event_id,
        "amount_cents": amount_cents,
        "reader_id": reader_id,
    }
    if currency:
        body["currency"] = currency
    if client_order_id:
        body["client_order_id"] = client_order_id
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return r.json()


async def terminate_sumup_checkout(*, event_id: int, reader_id: str) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sumup/terminate"
    body = {"event_id": event_id, "reader_id": reader_id}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return r.json()


async def get_sumup_checkout_status(*, event_id: int, checkout_id: str) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sumup/status"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers=_headers(cid, secret),
            params={"event_id": event_id, "checkout_id": checkout_id},
        )
        r.raise_for_status()
        return r.json()


async def unpair_device() -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/unpair"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"})
        if r.status_code >= 400:
            detail = (r.text or "").strip() or "Cloud unpair failed"
            raise CloudRequestError(r.status_code, detail)
        return r.json() if r.content else {"status": "revoked"}


async def fetch_screensaver_image(
    sha256: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, bytes]:
    """Download a screensaver image by content hash from cloud edge."""
    base, cid, secret = _require_config()
    key = (sha256 or "").strip().lower()
    url = f"{base}/edge/v1/screensaver/{key}"
    async with edge_http_client(client, timeout=60.0) as http:
        r = await http.get(url, headers=_headers(cid, secret))
        if r.status_code >= 400:
            detail = (r.text or "").strip() or "screensaver download failed"
            raise CloudRequestError(r.status_code, detail)
        mime = (r.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
        return mime, r.content
