"""ESC/POS document rendering via python-escpos (Dummy → bytes).

Transport (TCP, Bluetooth) stays in print_worker; callers only need the byte payload.
"""

from __future__ import annotations

import base64
import logging
import os
from collections.abc import Callable
from io import BytesIO

from escpos.printer import Dummy
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

# Typical 80 mm thermal printer printable width in dots.
DEFAULT_MAX_IMAGE_WIDTH = 384
# Epson TM family profile so python-escpos can center raster images.
DEFAULT_PRINTER_PROFILE = "TM-T88IV"


def escpos_logo_max_width() -> int:
    raw = os.getenv("ESCPOS_LOGO_MAX_WIDTH", str(DEFAULT_MAX_IMAGE_WIDTH)).strip()
    try:
        return max(128, int(raw))
    except ValueError:
        return DEFAULT_MAX_IMAGE_WIDTH


def new_slip() -> Dummy:
    try:
        return Dummy(profile=DEFAULT_PRINTER_PROFILE)
    except Exception:
        return Dummy()


def escpos_encoding() -> str:
    return os.getenv("ESCPOS_ENCODING", "cp858").strip() or "cp858"


def escpos_codepage() -> int:
    raw = os.getenv("ESCPOS_CODEPAGE", "19").strip()
    try:
        return int(raw)
    except ValueError:
        return 19


def escpos_init_preamble() -> bytes:
    """Initialize printer and select code page (PC858 default)."""
    return b"\x1b\x40" + bytes([0x1B, 0x74, escpos_codepage() & 0xFF])


def encode_escpos_text(text: str) -> bytes:
    return str(text).encode(escpos_encoding(), errors="replace")


def finish_slip(printer: Dummy, *, feed_lines: int = 2) -> bytes:
    if feed_lines > 0:
        printer.text("\n" * feed_lines)
    printer.cut()
    return escpos_init_preamble() + printer.output


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


def write_centered_sized(printer: Dummy, text: str, size: str = "large") -> None:
    printer.set(align="center")
    write_sized_line(printer, text, size)
    printer.set(align="left")


def write_separator(printer: Dummy, char: str = "-", width: int = 32) -> None:
    write_line(printer, char * width)


def write_two_column(
    printer: Dummy,
    left: str,
    right: str,
    width: int = 48,
    *,
    left_bold: bool = False,
) -> None:
    right = right or ""
    left = left or ""
    max_left = max(0, width - len(right) - 1)
    if len(left) > max_left:
        left = (left[: max_left - 1] + "…") if max_left > 1 else left[:max_left]
    pad = max(1, width - len(left) - len(right))
    if left_bold:
        printer.set(bold=True)
    printer.text(f"{left}{' ' * pad}{right}\n")
    printer.set(bold=False, double_height=False, double_width=False)


def _effective_line_width(width: int, size: str) -> int:
    key = (size or "normal").lower()
    if key in ("large", "xlarge"):
        return max(12, width // 2)
    return width


def _format_item_line(
    qty: int,
    name: str,
    cents: int,
    width: int,
    *,
    indent: int = 0,
) -> str:
    price = f"{cents / 100:.2f}"
    left = f"{' ' * indent}{qty} {name}".strip() if qty > 0 else f"{' ' * indent}{name}".strip()
    max_left = max(0, width - len(price) - 1)
    if len(left) > max_left:
        left = (left[: max_left - 1] + "…") if max_left > 1 else left[:max_left]
    pad = max(1, width - len(left) - len(price))
    return (left + (" " * pad) + price)[:width]


def write_item_row(
    printer: Dummy,
    qty: int,
    name: str,
    cents: int,
    width: int = 48,
    *,
    indent: int = 0,
    size: str = "normal",
) -> None:
    eff_width = _effective_line_width(width, size)
    line = _format_item_line(qty, name, cents, eff_width, indent=indent)
    key = (size or "normal").lower()
    if key in ("large", "xlarge"):
        write_sized_line(printer, line, key)
    else:
        printer.text(f"{line}\n")


def write_subline(printer: Dummy, text: str, *, indent: int = 2, size: str = "normal") -> None:
    line = f"{' ' * indent}{text}"
    key = (size or "normal").lower()
    if key in ("large", "xlarge"):
        write_sized_line(printer, line, key)
    else:
        printer.text(f"{line}\n")


def escpos_hero_scale() -> int:
    raw = os.getenv("ESCPOS_HERO_SCALE", "8").strip()
    try:
        return max(1, min(8, int(raw)))
    except ValueError:
        return 8


def _gs_char_size(width_mult: int, height_mult: int) -> bytes:
    w = max(1, min(8, width_mult))
    h = max(1, min(8, height_mult))
    n = (w - 1) | ((h - 1) << 4)
    return bytes([0x1D, 0x21, n])


def write_hero(
    printer: Dummy,
    text: str,
    size: str = "xlarge",
    *,
    magnification: int | None = None,
) -> None:
    key = (size or "xlarge").lower()
    printer.set(align="center")
    if key == "xlarge":
        scale = magnification if magnification is not None else escpos_hero_scale()
        scale = max(1, min(8, scale))
        printer._raw(_gs_char_size(scale, scale))
        printer.set(bold=True, double_height=False, double_width=False)
        printer.text(f"{text}\n")
        printer._raw(_gs_char_size(1, 1))
        printer.set(bold=False)
    elif key == "large":
        write_sized_line(printer, text, "large")
    else:
        write_sized_line(printer, text, "normal")
    printer.text("\n")
    printer.set(align="left")


def _prepare_receipt_logo(image_bytes: bytes, *, max_width: int) -> Image.Image:
    """Convert uploaded logo to centered 1-bit raster for thermal printing."""
    img = Image.open(BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        gray = background.convert("L")
    elif img.mode == "1":
        gray = img.convert("L")
    else:
        gray = img.convert("L")

    if gray.width > max_width:
        ratio = max_width / gray.width
        new_h = max(1, int(gray.height * ratio))
        gray = gray.resize((max_width, new_h), Image.Resampling.LANCZOS)

    # Dark pixels print; tune above mid-gray so light logo colors stay visible.
    mono = gray.point(lambda p: 0 if p < 175 else 255, mode="1")

    canvas = Image.new("1", (max_width, mono.height), 1)
    x_offset = max(0, (max_width - mono.width) // 2)
    canvas.paste(mono, (x_offset, 0))
    return canvas


def write_logo_bytes(
    printer: Dummy,
    image_bytes: bytes,
    *,
    max_width: int | None = None,
    center: bool = True,
) -> None:
    """Rasterize image bytes for ESC/POS (PNG/JPEG/etc.). Skips on failure."""
    if not image_bytes:
        return
    width = max_width if max_width is not None else escpos_logo_max_width()
    try:
        img = _prepare_receipt_logo(image_bytes, max_width=width)
        printer.set(align="center")
        printer.image(img, center=center, impl="bitImageRaster")
        printer.set(align="left")
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
