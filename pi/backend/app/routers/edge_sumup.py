"""SumUp Cloud checkout proxy routes."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..cloud_client import (
    CloudConfigError,
)
from ..cloud_client import (
    create_sumup_checkout as cloud_create_sumup_checkout,
)
from ..cloud_client import (
    get_sumup_checkout_status as cloud_get_sumup_checkout_status,
)
from ..cloud_client import (
    terminate_sumup_checkout as cloud_terminate_sumup_checkout,
)
from ..deps import get_db
from .edge_common import _event_payment_types
from .edge_http import cloud_config_http_error, cloud_gateway_http_error

router = APIRouter()


class SumupCheckoutBody(BaseModel):
    event_id: int
    amount_cents: int = Field(..., gt=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    reader_id: str = Field(..., min_length=1, max_length=64)
    client_order_id: str | None = Field(None, max_length=64)


class SumupTerminateBody(BaseModel):
    event_id: int
    reader_id: str = Field(..., min_length=1, max_length=64)


def _sumup_event_or_error(db: Session, event_id: int) -> dict:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found in local bundle")
    if "sumup_connected" not in _event_payment_types(ev):
        raise HTTPException(status_code=403, detail="SumUp connected is not enabled for this event")
    return ev


@router.post("/v1/sumup/checkout")
async def sumup_checkout(body: SumupCheckoutBody, db: Session = Depends(get_db)) -> dict:
    ev = _sumup_event_or_error(db, body.event_id)
    try:
        return await cloud_create_sumup_checkout(
            event_id=body.event_id,
            amount_cents=body.amount_cents,
            currency=body.currency or ev.get("currency"),
            reader_id=body.reader_id,
            client_order_id=body.client_order_id,
        )
    except CloudConfigError as e:
        raise cloud_config_http_error(e) from e
    except httpx.HTTPStatusError as e:
        raise cloud_gateway_http_error(e) from e


@router.post("/v1/sumup/terminate")
async def sumup_terminate(body: SumupTerminateBody, db: Session = Depends(get_db)) -> dict:
    _sumup_event_or_error(db, body.event_id)
    try:
        return await cloud_terminate_sumup_checkout(event_id=body.event_id, reader_id=body.reader_id)
    except CloudConfigError as e:
        raise cloud_config_http_error(e) from e
    except httpx.HTTPStatusError as e:
        raise cloud_gateway_http_error(e) from e


@router.get("/v1/sumup/status")
async def sumup_status(
    event_id: int = Query(...),
    checkout_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
) -> dict:
    _sumup_event_or_error(db, event_id)
    try:
        return await cloud_get_sumup_checkout_status(event_id=event_id, checkout_id=checkout_id)
    except CloudConfigError as e:
        raise cloud_config_http_error(e) from e
    except httpx.HTTPStatusError as e:
        raise cloud_gateway_http_error(e) from e
