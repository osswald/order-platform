"""Hosted-Pi operational purge (Play review cleanup)."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..event_lifecycle import purge_bundle_events_operational
from .edge_admin import bundle_dict_optional

router = APIRouter()


class PurgeOperationalResponse(BaseModel):
    ok: bool = True
    purged_event_ids: list[int] = Field(default_factory=list)


def _require_hosted_cleanup_secret(secret: str | None) -> None:
    if os.getenv("HOSTED_PI", "").strip() != "1":
        raise HTTPException(status_code=404, detail="Not Found")
    expected = os.getenv("PLAY_REVIEW_CLEANUP_SECRET", "").strip()
    if not expected or not secret or secret != expected:
        raise HTTPException(status_code=401, detail="Invalid cleanup secret")


@router.post("/v1/ops/purge-operational", response_model=PurgeOperationalResponse)
def purge_operational(
    db: Session = Depends(get_db),
    x_cleanup_secret: Annotated[str | None, Header()] = None,
) -> PurgeOperationalResponse:
    """Purge demo operational data without changing event status (test→prod semantics)."""
    _require_hosted_cleanup_secret(x_cleanup_secret)
    bundle = bundle_dict_optional(db) or {}
    purged = purge_bundle_events_operational(db, bundle)
    return PurgeOperationalResponse(ok=True, purged_event_ids=purged)
