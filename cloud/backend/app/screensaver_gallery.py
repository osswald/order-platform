"""Organisation screensaver gallery storage and manifest helpers."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from sqlalchemy.orm import Session

from .models import Organisation, OrganisationScreensaverImage

ALLOWED_SCREENSAVER_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
MAX_SCREENSAVER_IMAGE_BYTES = 10 * 1024 * 1024
MAX_SCREENSAVER_GALLERY_IMAGES = 10


class ScreensaverImageError(ValueError):
    """Typed validation error mapped to a localized API error code."""

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(code)


def _normalize_mime(mime: str) -> str:
    normalized = (mime or "").split(";")[0].strip().lower()
    if normalized == "image/jpg":
        normalized = "image/jpeg"
    return normalized


def sniff_screensaver_mime(raw_bytes: bytes) -> str | None:
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(raw_bytes) >= 12 and raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_screensaver_image(mime: str, raw_bytes: bytes) -> str:
    if not raw_bytes:
        raise ScreensaverImageError("screensaver_file_empty")
    if len(raw_bytes) > MAX_SCREENSAVER_IMAGE_BYTES:
        raise ScreensaverImageError(
            "screensaver_file_too_large",
            max_mb=MAX_SCREENSAVER_IMAGE_BYTES // (1024 * 1024),
        )
    sniffed = sniff_screensaver_mime(raw_bytes)
    declared = _normalize_mime(mime)
    if sniffed in ALLOWED_SCREENSAVER_MIMES:
        return sniffed
    if declared in ALLOWED_SCREENSAVER_MIMES:
        return declared
    raise ScreensaverImageError("screensaver_invalid_type")


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
        raise ScreensaverImageError(
            "screensaver_gallery_full",
            max=MAX_SCREENSAVER_GALLERY_IMAGES,
        )
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
