"""HTTP client for the hosted-pi-manager orchestrator service."""

from __future__ import annotations

import os

import httpx

MANAGER_URL = os.getenv("HOSTED_PI_MANAGER_URL", "http://hosted-pi-manager:8090").rstrip("/")
MANAGER_SECRET = os.getenv("HOSTED_PI_MANAGER_SECRET", "")


class HostedPiManagerError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Hosted Pi manager error ({status_code}): {detail}")


def _headers() -> dict[str, str]:
    if not MANAGER_SECRET:
        return {}
    return {"X-Manager-Secret": MANAGER_SECRET}


async def provision_instance(
    *,
    slug: str,
    cloud_base_url: str,
    edge_client_id: str,
    edge_secret: str,
) -> None:
    payload = {
        "slug": slug,
        "cloud_base_url": cloud_base_url,
        "edge_client_id": edge_client_id,
        "edge_secret": edge_secret,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{MANAGER_URL}/internal/instances", json=payload, headers=_headers())
        if response.status_code >= 400:
            raise HostedPiManagerError(response.status_code, response.text[:2000])


async def destroy_instance(slug: str) -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.delete(f"{MANAGER_URL}/internal/instances/{slug}", headers=_headers())
        if response.status_code >= 400:
            raise HostedPiManagerError(response.status_code, response.text[:2000])
