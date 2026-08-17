"""Serve locally cached screensaver images to the customer display."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..bundle_cache import get_bundle_dict
from ..deps import get_db
from ..screensaver_display import jpeg_bytes_for_display
from ..screensaver_store import (
    has_screensaver_file,
    list_local_shas,
    manifest_shas,
    read_screensaver_bytes,
)

router = APIRouter()


@router.get("/v1/screensaver/images")
def list_screensaver_images(
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """List screensaver images available locally for the current organisation bundle."""
    try:
        bundle = get_bundle_dict(db)
    except Exception:
        return {"event_id": event_id, "images": [], "greyscale": False}
    manifest = manifest_shas(bundle if isinstance(bundle, dict) else None)
    local = list_local_shas()
    images = [
        {"sha256": row["sha256"], "mime": row.get("mime") or "application/octet-stream"}
        for row in manifest
        if row["sha256"] in local
    ]
    greyscale = bool(isinstance(bundle, dict) and bundle.get("screensaver_greyscale"))
    return {"event_id": event_id, "images": images, "greyscale": greyscale}


@router.get("/v1/screensaver/{sha256}")
def get_screensaver_image(sha256: str) -> Response:
    if not has_screensaver_file(sha256):
        raise HTTPException(status_code=404, detail="Screensaver image not found")
    raw = read_screensaver_bytes(sha256)
    if raw is None:
        raise HTTPException(status_code=404, detail="Screensaver image not found")
    try:
        body, mime = jpeg_bytes_for_display(raw)
    except OSError as exc:
        raise HTTPException(status_code=422, detail="Screensaver image could not be decoded") from exc
    return Response(content=body, media_type=mime)
