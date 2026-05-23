"""TWINT QR image storage helpers for events."""

from __future__ import annotations

import base64

from .payment_types_config import payment_types_from_event

ALLOWED_TWINT_QR_MIMES = frozenset({"image/png", "image/svg+xml"})
MAX_TWINT_QR_BYTES = 500 * 1024


def has_twint_qr(event) -> bool:
    mime = getattr(event, "twint_qr_mime", None)
    data = getattr(event, "twint_qr_data", None)
    return bool(mime and data)


def twint_qr_data_url_for_event(event) -> str | None:
    """Data URL for Pi bundle when TWINT is enabled and QR exists."""
    types = payment_types_from_event(event)
    if "twint" not in types:
        return None
    mime = getattr(event, "twint_qr_mime", None)
    data = getattr(event, "twint_qr_data", None)
    if not mime or not data:
        return None
    return f"data:{mime};base64,{data}"


def store_twint_qr(event, mime: str, raw_bytes: bytes) -> None:
    if mime not in ALLOWED_TWINT_QR_MIMES:
        raise ValueError("File must be PNG or SVG")
    if len(raw_bytes) > MAX_TWINT_QR_BYTES:
        raise ValueError(f"File too large (max {MAX_TWINT_QR_BYTES // 1024} KB)")
    event.twint_qr_mime = mime
    event.twint_qr_data = base64.b64encode(raw_bytes).decode("ascii")


def clear_twint_qr(event) -> None:
    event.twint_qr_mime = None
    event.twint_qr_data = None


def twint_qr_bytes(event) -> tuple[str, bytes] | None:
    if not has_twint_qr(event):
        return None
    return event.twint_qr_mime, base64.b64decode(event.twint_qr_data)
