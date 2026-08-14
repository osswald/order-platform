"""Serve locally cached screensaver images to the customer display."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..bundle_cache import get_bundle_dict
from ..deps import get_db
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
        return {"event_id": event_id, "images": []}
    manifest = manifest_shas(bundle if isinstance(bundle, dict) else None)
    local = list_local_shas()
    images = [
        {"sha256": row["sha256"], "mime": row.get("mime") or "application/octet-stream"}
        for row in manifest
        if row["sha256"] in local
    ]
    return {"event_id": event_id, "images": images}


@router.get("/v1/screensaver/{sha256}")
def get_screensaver_image(sha256: str) -> Response:
    if not has_screensaver_file(sha256):
        raise HTTPException(status_code=404, detail="Screensaver image not found")
    raw = read_screensaver_bytes(sha256)
    if raw is None:
        raise HTTPException(status_code=404, detail="Screensaver image not found")
    # Prefer sniffing common magic bytes for Content-Type.
    mime = "application/octet-stream"
    if raw.startswith(b"\x89PNG"):
        mime = "image/png"
    elif raw[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif raw.startswith(b"RIFF") and b"WEBP" in raw[:16]:
        mime = "image/webp"
    return Response(content=raw, media_type=mime)
