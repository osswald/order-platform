"""Downscale screensaver originals for customer-display playback."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps

DISPLAY_MAX_EDGE = 1920
DISPLAY_JPEG_QUALITY = 82


def jpeg_bytes_for_display(raw: bytes, *, max_edge: int = DISPLAY_MAX_EDGE) -> tuple[bytes, str]:
    """Return JPEG bytes fit to ``max_edge``, preserving aspect ratio.

    Camera originals (e.g. 6000×4000) are too large for Android WebView / Elo
    kiosk decode. The content-addressed store keeps the original; only the
    customer-display HTTP response is resized.
    """
    img = Image.open(BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, format="JPEG", quality=DISPLAY_JPEG_QUALITY, optimize=True)
    return out.getvalue(), "image/jpeg"
