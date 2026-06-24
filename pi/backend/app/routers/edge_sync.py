"""Sync, bundle, and cloud reachability routes."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..bundle_cache import get_bundle_dict
from ..cloud_client import CloudConfigError, ping_cloud_reachable
from ..datetime_util import utc_iso
from ..deps import get_db
from ..models import SyncedBundle
from ..schemas.bundle import EdgeBundleResponse
from ..schemas.edge import (
    CloudReachableResponse,
    SyncMetaResponse,
    SyncPullResponse,
    SyncPushResponse,
    SyncStatusResponse,
)
from ..sync_service import (
    is_cloud_configured,
    pending_outbox_count,
    pull_and_restore,
    push_outbox,
    sync_cycle_lock,
    sync_status,
)
from .edge_http import cloud_config_http_error, cloud_gateway_http_error

router = APIRouter()


@router.get("/v1/cloud/reachable", response_model=CloudReachableResponse)
async def get_cloud_reachable() -> CloudReachableResponse:
    if not is_cloud_configured():
        return CloudReachableResponse(reachable=False, reason="not_configured")
    reachable, reason = await ping_cloud_reachable()
    return CloudReachableResponse(reachable=reachable, reason=reason)


@router.get("/v1/sync/status", response_model=SyncStatusResponse)
def get_sync_status(db: Session = Depends(get_db)) -> SyncStatusResponse:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    last_sync_at = utc_iso(row.updated_at) if row and row.updated_at else None
    return SyncStatusResponse.model_validate({
        **sync_status,
        "configured": is_cloud_configured(),
        "pending_outbox_count": pending_outbox_count(db),
        "bundle_last_sync_at": last_sync_at,
    })


@router.post("/v1/sync/pull", response_model=SyncPullResponse)
async def sync_pull(db: Session = Depends(get_db)) -> SyncPullResponse:
    async with sync_cycle_lock:
        try:
            result = await pull_and_restore(db)
        except CloudConfigError as e:
            raise cloud_config_http_error(e) from e
        except httpx.HTTPStatusError as e:
            raise cloud_gateway_http_error(e) from e
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail="Cloud bundle endpoint could not be reached",
            ) from e
    return SyncPullResponse(ok=True, event_count=result["event_count"])


@router.get("/v1/bundle", response_model=EdgeBundleResponse)
def get_bundle(db: Session = Depends(get_db)) -> EdgeBundleResponse:
    return EdgeBundleResponse.model_validate(get_bundle_dict(db))


@router.get("/v1/meta", response_model=SyncMetaResponse)
def get_meta(db: Session = Depends(get_db)) -> SyncMetaResponse:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row:
        return SyncMetaResponse(last_sync_at=None)
    return SyncMetaResponse(last_sync_at=utc_iso(row.updated_at) if row.updated_at else None)


@router.post("/v1/sync/push", response_model=SyncPushResponse)
async def sync_push(db: Session = Depends(get_db)) -> SyncPushResponse:
    async with sync_cycle_lock:
        try:
            result = await push_outbox(db, retry_errors=False)
            return SyncPushResponse.model_validate(result)
        except CloudConfigError as e:
            raise cloud_config_http_error(e) from e
        except httpx.HTTPStatusError as e:
            raise cloud_gateway_http_error(e) from e
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail="Cloud sync endpoint could not be reached",
            ) from e
