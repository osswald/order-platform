import os

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..edge_config import is_edge_configured, read_edge_config, write_edge_config

router = APIRouter(prefix="/v1/setup")

DEFAULT_CLOUD_BASE_URL = os.environ.get("DEFAULT_CLOUD_BASE_URL", "https://api.vendiqo.ch")
SETUP_URL = "http://192.168.192.10"


class SetupStatusResponse(BaseModel):
    configured: bool
    setup_url: str = SETUP_URL
    cloud_base_url: str | None = None
    edge_client_id: str | None = None


class PairSetupRequest(BaseModel):
    pairing_code: str = Field(..., min_length=6, max_length=32)
    cloud_base_url: str = Field(DEFAULT_CLOUD_BASE_URL, min_length=1, max_length=255)
    device_name: str | None = Field(None, max_length=255)


class PairSetupResponse(SetupStatusResponse):
    appliance_id: int
    appliance_name: str | None = None


def _status_from_config() -> SetupStatusResponse:
    values = read_edge_config()
    configured = is_edge_configured()
    return SetupStatusResponse(
        configured=configured,
        cloud_base_url=values["CLOUD_BASE_URL"] or DEFAULT_CLOUD_BASE_URL,
        edge_client_id=values["EDGE_CLIENT_ID"] or None,
    )


@router.get("/status", response_model=SetupStatusResponse)
def read_setup_status():
    return _status_from_config()


@router.post("/pair", response_model=PairSetupResponse)
async def pair_with_cloud(body: PairSetupRequest):
    cloud_base_url = body.cloud_base_url.strip().rstrip("/")
    if not cloud_base_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cloud URL must start with http:// or https://",
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{cloud_base_url}/edge/v1/pair",
                json={
                    "pairing_code": body.pairing_code,
                    "device_name": body.device_name,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or "Pairing rejected by cloud"
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloud pairing endpoint could not be reached",
        ) from exc

    edge_client_id = (payload.get("edge_client_id") or "").strip()
    edge_secret = (payload.get("edge_secret") or "").strip()
    if not edge_client_id or not edge_secret:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloud pairing response did not include edge credentials",
        )

    write_edge_config(
        cloud_base_url=cloud_base_url,
        edge_client_id=edge_client_id,
        edge_secret=edge_secret,
    )
    return PairSetupResponse(
        configured=True,
        cloud_base_url=cloud_base_url,
        edge_client_id=edge_client_id,
        appliance_id=int(payload.get("appliance_id") or 0),
        appliance_name=payload.get("appliance_name"),
    )
