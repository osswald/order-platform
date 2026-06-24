"""Cached organisation bundle helpers."""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import SyncedBundle


def get_bundle_dict(db: Session) -> dict:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        raise HTTPException(status_code=400, detail="No bundle; run POST /v1/sync/pull first")
    data = json.loads(row.json_body)
    if not isinstance(data, dict) or data.get("organisation_id") is None:
        raise HTTPException(status_code=400, detail="No bundle; run POST /v1/sync/pull first")
    return data


def event_from_bundle(bundle: dict, event_id: int) -> dict | None:
    for ev in bundle.get("events", []) or []:
        if int(ev["id"]) == int(event_id):
            return ev
    return None


def get_bundle_dict_raw(db: Session) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    return data if isinstance(data, dict) else None
