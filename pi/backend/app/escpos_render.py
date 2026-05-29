"""ESC/POS document rendering via python-escpos (Dummy → bytes).

Transport (TCP, Bluetooth) stays in print_worker; callers only need the byte payload.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from io import BytesIO

from escpos.printer import Dummy
from PIL import Image

log = logging.getLogger(__name__)

# Typical 80 mm thermal printer printable width in dots.
DEFAULT_MAX_IMAGE_WIDTH = 384


def new_slip() -> Dummy:
    return Dummy()


def finish_slip(printer: Dummy, *, feed_lines: int = 2) -> bytes:
    if feed_lines > 0:
        printer.text("\n" * feed_lines)
    printer.cut()
    return printer.output


def render_slip(render_fn: Callable[[Dummy], None], *, feed_lines: int = 2) -> bytes:
    printer = new_slip()
    render_fn(printer)
    return finish_slip(printer, feed_lines=feed_lines)


def write_heading(printer: Dummy, text: str) -> None:
    write_sized_line(printer, text, "large")


def write_line(printer: Dummy, text: str) -> None:
    write_sized_line(printer, text, "normal")


def write_sized_line(printer: Dummy, text: str, size: str = "normal") -> None:
    key = (size or "normal").lower()
    if key == "xlarge":
        printer.set(bold=True, double_height=True, double_width=True)
    elif key == "large":
        printer.set(bold=True, double_height=True, double_width=False)
    else:
        printer.set(bold=False, double_height=False, double_width=False)
    printer.text(f"{text}\n")
    printer.set(bold=False, double_height=False, double_width=False)


def write_centered_block(printer: Dummy, text: str) -> None:
    block = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not block:
        return
    printer.set(align="center")
    for line in block.split("\n"):
        printer.text(f"{line}\n")
    printer.set(align="left")


def write_separator(printer: Dummy, char: str = "-", width: int = 32) -> None:
    write_line(printer, char * width)


def write_logo_bytes(
    printer: Dummy,
    image_bytes: bytes,
    *,
    max_width: int = DEFAULT_MAX_IMAGE_WIDTH,
    center: bool = True,
) -> None:
    """Rasterize image bytes for ESC/POS (PNG/JPEG/etc.). Skips on failure."""
    if not image_bytes:
        return
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode not in ("1", "L"):
            img = img.convert("L")
        if max_width and img.width > max_width:
            ratio = max_width / img.width
            new_h = max(1, int(img.height * ratio))
            img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
        if img.mode != "1":
            img = img.point(lambda p: 0 if p < 128 else 255, mode="1")
        printer.image(img, center=center)
        printer.text("\n")
    except Exception:
        log.warning("ESC/POS logo render failed", exc_info=True)


def write_logo_from_event(printer: Dummy, ev: dict | None, *, logo_enabled: bool = True) -> None:
    """Print event logo when bundle provides base64 or raw bytes under printing config."""
    if not ev or not logo_enabled:
        return
    printing = (ev.get("configuration") or {}).get("printing") or {}
    logo_b64 = printing.get("logo_base64") or printing.get("receipt_logo_base64")
    if not logo_b64 or not isinstance(logo_b64, str):
        return
    try:
        raw = base64.b64decode(logo_b64, validate=True)
    except Exception:
        log.warning("Invalid receipt logo base64 on event %s", ev.get("id"))
        return
    write_logo_bytes(printer, raw)
