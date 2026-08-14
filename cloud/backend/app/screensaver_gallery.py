"""Organisation screensaver gallery storage and manifest helpers."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from sqlalchemy.orm import Session

from .models import Organisation, OrganisationScreensaverImage

ALLOWED_SCREENSAVER_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
MAX_SCREENSAVER_IMAGE_BYTES = 3 * 1024 * 1024
MAX_SCREENSAVER_GALLERY_IMAGES = 10


def _normalize_mime(mime: str) -> str:
    normalized = (mime or "").split(";")[0].strip().lower()
    if normalized == "image/jpg":
        normalized = "image/jpeg"
    return normalized


def validate_screensaver_image(mime: str, raw_bytes: bytes) -> str:
    normalized = _normalize_mime(mime)
    if normalized not in ALLOWED_SCREENSAVER_MIMES:
        raise ValueError("File must be JPEG, PNG, or WebP")
    if len(raw_bytes) > MAX_SCREENSAVER_IMAGE_BYTES:
        raise ValueError(f"File too large (max {MAX_SCREENSAVER_IMAGE_BYTES // (1024 * 1024)} MB)")
    if not raw_bytes:
        raise ValueError("File is empty")
    return normalized


def gallery_count(db: Session, organisation_id: int) -> int:
    return (
        db.query(OrganisationScreensaverImage)
        .filter(OrganisationScreensaverImage.organisation_id == organisation_id)
        .count()
    )


def get_by_sha256(
    db: Session,
    organisation_id: int,
    sha256: str,
) -> OrganisationScreensaverImage | None:
    return (
        db.query(OrganisationScreensaverImage)
        .filter(
            OrganisationScreensaverImage.organisation_id == organisation_id,
            OrganisationScreensaverImage.sha256 == sha256,
        )
        .first()
    )


def list_screensaver_images(db: Session, organisation_id: int) -> list[OrganisationScreensaverImage]:
    return (
        db.query(OrganisationScreensaverImage)
        .filter(OrganisationScreensaverImage.organisation_id == organisation_id)
        .order_by(OrganisationScreensaverImage.id)
        .all()
    )


def list_screensaver_manifest(db: Session, organisation_id: int) -> list[dict[str, str]]:
    rows = list_screensaver_images(db, organisation_id)
    return [{"sha256": row.sha256, "mime": row.mime} for row in rows]


def store_screensaver_image(
    db: Session,
    organisation: Organisation,
    mime: str,
    raw_bytes: bytes,
) -> OrganisationScreensaverImage:
    normalized = validate_screensaver_image(mime, raw_bytes)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    existing = get_by_sha256(db, organisation.id, digest)
    if existing is not None:
        return existing
    if gallery_count(db, organisation.id) >= MAX_SCREENSAVER_GALLERY_IMAGES:
        raise ValueError(f"Gallery full (max {MAX_SCREENSAVER_GALLERY_IMAGES} images)")
    row = OrganisationScreensaverImage(
        organisation_id=organisation.id,
        sha256=digest,
        mime=normalized,
        data=base64.b64encode(raw_bytes).decode("ascii"),
    )
    db.add(row)
    db.flush()
    return row


def delete_screensaver_image(db: Session, organisation_id: int, image_id: int) -> bool:
    row = (
        db.query(OrganisationScreensaverImage)
        .filter(
            OrganisationScreensaverImage.organisation_id == organisation_id,
            OrganisationScreensaverImage.id == image_id,
        )
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    return True


def screensaver_image_bytes(row: OrganisationScreensaverImage) -> tuple[str, bytes]:
    return row.mime, base64.b64decode(row.data)


def image_to_read_dict(row: OrganisationScreensaverImage) -> dict[str, Any]:
    return {
        "id": row.id,
        "sha256": row.sha256,
        "mime": row.mime,
        "created_at": row.created_at,
    }
