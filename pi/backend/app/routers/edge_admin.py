"""Pi edge admin routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import SyncedBundle
from ..schemas.edge import AdminStatusResponse, AdminVerifyBody, OkResponse
from ..security import verify_password

router = APIRouter()


def bundle_dict_optional(db: Session) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    if not isinstance(data, dict) or data.get("organisation_id") is None:
        return None
    return data


@router.get("/v1/admin/status", response_model=AdminStatusResponse)
def admin_status(db: Session = Depends(get_db)) -> AdminStatusResponse:
    bundle = bundle_dict_optional(db)
    bundle_ready = bundle is not None
    hashes = (bundle or {}).get("admin_pin_hashes") or []
    return AdminStatusResponse(
        bundle_ready=bundle_ready,
        requires_pin=bundle_ready and len(hashes) > 0,
    )


@router.post("/v1/admin/verify", response_model=OkResponse)
def verify_admin_pin(body: AdminVerifyBody, db: Session = Depends(get_db)) -> OkResponse:
    if not body.pin.isdigit():
        raise HTTPException(status_code=401, detail="Invalid admin code")
    bundle = bundle_dict_optional(db)
    if bundle is None:
        raise HTTPException(status_code=401, detail="Invalid admin code")
    hashes = bundle.get("admin_pin_hashes") or []
    if not hashes:
        raise HTTPException(status_code=401, detail="no_admin_pins_configured")
    for h in hashes:
        if not h or not isinstance(h, str):
            continue
        try:
            if verify_password(body.pin, h):
                return OkResponse()
        except Exception:
            continue
    raise HTTPException(status_code=401, detail="Invalid admin code")
