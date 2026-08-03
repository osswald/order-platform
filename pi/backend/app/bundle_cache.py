"""Cached organisation bundle helpers."""

from __future__ import annotations

import copy
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import SyncedBundle

_cached_bundle: dict[str, Any] | None = None


def invalidate_bundle_cache() -> None:
    """Drop the in-process organisation bundle (force next read from SQLite)."""
    global _cached_bundle
    _cached_bundle = None


def set_bundle_cache(data: dict[str, Any] | None) -> None:
    """Replace process memory with a deep copy of ``data`` (or clear if None)."""
    global _cached_bundle
    _cached_bundle = None if data is None else copy.deepcopy(data)


def get_bundle_dict(db: Session) -> dict:
    data = get_bundle_dict_raw(db)
    if data is None or data.get("organisation_id") is None:
        raise HTTPException(status_code=400, detail="No bundle; run POST /v1/sync/pull first")
    return data


def event_from_bundle(bundle: dict, event_id: int) -> dict | None:
    for ev in bundle.get("events", []) or []:
        if int(ev["id"]) == int(event_id):
            return ev
    return None


def get_bundle_dict_raw(db: Session) -> dict | None:
    global _cached_bundle
    if _cached_bundle is not None:
        return copy.deepcopy(_cached_bundle)

    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    if not isinstance(data, dict):
        return None
    _cached_bundle = copy.deepcopy(data)
    return copy.deepcopy(_cached_bundle)
