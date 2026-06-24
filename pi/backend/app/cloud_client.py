"""Pull/push against cloud edge API."""

import json
from typing import Any

import httpx

from .edge_config import read_edge_config


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
    return {
        "X-Edge-Client-Id": client_id,
        "X-Edge-Secret": secret,
    }


async def fetch_bundle() -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/bundle"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers=_headers(cid, secret))
        r.raise_for_status()
        return r.json()


async def fetch_bundle_manifest() -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/bundle/manifest"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=_headers(cid, secret))
        r.raise_for_status()
        return r.json()


async def fetch_bundle_chunk(*, section: str, cursor: str | None = None) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/bundle/chunk"
    params: dict[str, str] = {"section": section}
    if cursor:
        params["cursor"] = cursor
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers=_headers(cid, secret), params=params)
        r.raise_for_status()
        return r.json()


async def submit_order(client_order_id: str, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/orders"
    body = {"client_order_id": client_order_id, "event_id": event_id, "payload": payload}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return r.json()


async def submit_operational_chunk(
    *,
    chunk_id: str,
    event_id: int,
    entity_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sync/operational/chunk"
    body = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": entity_type,
        "payload": payload,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        if r.status_code == 404:
            client_order_id = str(payload.get("client_order_id") or chunk_id)
            return await submit_order(client_order_id, event_id, payload)
        r.raise_for_status()
        return r.json()


async def fetch_operational_snapshot(*, event_id: int | None = None) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/sync/operational/snapshot"
    params: dict[str, str] = {}
    if event_id is not None:
        params["event_id"] = str(event_id)
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers=_headers(cid, secret), params=params or None)
        r.raise_for_status()
        return r.json()


async def ping_cloud_reachable() -> tuple[bool, str | None]:
    """Return whether the Pi can reach the cloud API (for Terminal gating)."""
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


async def create_terminal_connection_token(event_id: int) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/terminal/connection-token"
    body = {"event_id": event_id}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return r.json()


async def create_terminal_payment_intent(
    *,
    event_id: int,
    amount_cents: int,
    currency: str | None = None,
    client_order_id: str | None = None,
    idempotency_key: str | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/terminal/payment-intents"
    body: dict[str, Any] = {
        "event_id": event_id,
        "amount_cents": amount_cents,
        "metadata": metadata or {},
    }
    if currency:
        body["currency"] = currency
    if client_order_id:
        body["client_order_id"] = client_order_id
    if idempotency_key:
        body["idempotency_key"] = idempotency_key
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return r.json()


async def retrieve_terminal_payment_intent(*, event_id: int, payment_intent_id: str) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/terminal/payment-intents/{payment_intent_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=_headers(cid, secret), params={"event_id": event_id})
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
