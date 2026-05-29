"""python-escpos rendering helpers."""

import base64
from io import BytesIO

from PIL import Image

from app.escpos_render import render_slip, write_heading, write_line, write_logo_bytes


def test_render_slip_contains_text():
    raw = render_slip(lambda p: (write_heading(p, "Test"), write_line(p, "Line")))
    assert b"Test" in raw
    assert b"Line" in raw


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
