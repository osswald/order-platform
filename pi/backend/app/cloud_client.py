"""Pull/push against cloud edge API."""

import os
from typing import Any

import httpx


class CloudConfigError(Exception):
    """Raised when required cloud / edge env vars are missing or blank."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing or empty: {', '.join(missing)}")


def _resolve_config() -> tuple[str, str, str]:
    base = (os.environ.get("CLOUD_BASE_URL") or "").strip().rstrip("/")
    cid = (os.environ.get("EDGE_CLIENT_ID") or "").strip()
    secret = (os.environ.get("EDGE_SECRET") or "").strip()
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


async def submit_order(client_order_id: str, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    base, cid, secret = _require_config()
    url = f"{base}/edge/v1/orders"
    body = {"client_order_id": client_order_id, "event_id": event_id, "payload": payload}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers={**_headers(cid, secret), "Content-Type": "application/json"}, json=body)
        r.raise_for_status()
        return r.json()
