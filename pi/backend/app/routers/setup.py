import os
import secrets

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..edge_config import clear_edge_config, is_edge_configured, read_edge_config, write_edge_config
from ..setup_cloud import DEFAULT_CLOUD_BASE_URL, allow_cloud_url_override, resolve_cloud_base_url

router = APIRouter(prefix="/v1/setup")

SETUP_URL = "http://192.168.192.10"


class SetupStatusResponse(BaseModel):
    configured: bool
    setup_url: str = SETUP_URL
    cloud_base_url: str | None = None
    edge_client_id: str | None = None
    allow_cloud_url_override: bool = False
    can_unpair: bool = False


class PairSetupRequest(BaseModel):
    pairing_code: str = Field(..., min_length=6, max_length=32)
    cloud_base_url: str = Field(DEFAULT_CLOUD_BASE_URL, min_length=1, max_length=255)
    device_name: str | None = Field(None, max_length=255)


class UnpairSetupRequest(BaseModel):
    unpair_secret: str = Field(..., min_length=1, max_length=255)


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
        allow_cloud_url_override=allow_cloud_url_override(),
        can_unpair=bool(os.getenv("PI_SETUP_UNPAIR_SECRET", "").strip()),
    )


def _require_unpair_secret(secret: str) -> None:
    expected = os.getenv("PI_SETUP_UNPAIR_SECRET", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unpair is disabled on this device",
        )
    if not secrets.compare_digest(secret, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid unpair secret")


@router.get("/status", response_model=SetupStatusResponse)
def read_setup_status():
    return _status_from_config()


@router.post("/unpair", response_model=SetupStatusResponse)
def unpair_device(body: UnpairSetupRequest) -> SetupStatusResponse:
    _require_unpair_secret(body.unpair_secret)
    clear_edge_config()
    return _status_from_config()


@router.post("/pair", response_model=PairSetupResponse)
async def pair_with_cloud(body: PairSetupRequest):
    if is_edge_configured():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pi is already paired; unpair before pairing again",
        )

    try:
        cloud_base_url = resolve_cloud_base_url(body.cloud_base_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

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
    status_body = _status_from_config()
    return PairSetupResponse(
        **status_body.model_dump(),
        appliance_id=int(payload.get("appliance_id") or 0),
        appliance_name=payload.get("appliance_name"),
    )
