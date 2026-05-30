"""python-escpos rendering helpers."""

import base64
from io import BytesIO

from PIL import Image

from app.escpos_render import (
    _prepare_receipt_logo,
    render_slip,
    write_heading,
    write_line,
    write_logo_bytes,
)


def test_render_slip_contains_text():
    raw = render_slip(lambda p: (write_heading(p, "Test"), write_line(p, "Line")))
    assert b"Test" in raw
    assert b"Line" in raw


def test_prepare_receipt_logo_rgba_centered_on_canvas():
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    for x in range(10, 30):
        for y in range(5, 15):
            img.putpixel((x, y), (20, 40, 80, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    prepared = _prepare_receipt_logo(buf.getvalue(), max_width=64)
    assert prepared.size == (64, 20)
    assert prepared.mode == "1"
    bbox = prepared.getbbox()
    assert bbox is not None
    assert bbox[0] >= 8


def test_write_logo_bytes_embeds_raster():
    img = Image.new("1", (32, 16), 1)
    for x in range(8):
        for y in range(4):
            img.putpixel((x, y), 0)
    buf = BytesIO()
    img.save(buf, format="PNG")
    logo_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    def render(p):
        write_logo_bytes(p, base64.b64decode(logo_b64))
        write_line(p, "After logo")

    raw = render_slip(render)
    assert b"After logo" in raw
    assert len(raw) > 40
