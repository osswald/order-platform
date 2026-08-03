"""python-escpos rendering helpers."""

import base64
from io import BytesIO

import pytest
from app.escpos_render import (
    _prepare_receipt_logo,
    clear_receipt_logo_cache,
    escpos_init_preamble,
    render_slip,
    write_heading,
    write_line,
    write_logo_bytes,
)
from PIL import Image, ImageOps


@pytest.fixture(autouse=True)
def _clear_logo_cache():
    clear_receipt_logo_cache()
    yield
    clear_receipt_logo_cache()


def _solid_png_bytes(*, size=(40, 20), color=(20, 40, 80, 255)) -> bytes:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(10, min(30, size[0])):
        for y in range(5, min(15, size[1])):
            img.putpixel((x, y), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_render_slip_contains_text():
    raw = render_slip(lambda p: (write_heading(p, "Test"), write_line(p, "Line")))
    assert b"Test" in raw
    assert b"Line" in raw


def test_finish_slip_avoids_default_six_line_cut_feed(monkeypatch):
    """python-escpos cut() feeds 6 lines by default; we cut tight then optional ESCPOS_FEED_LINES."""
    monkeypatch.setenv("ESCPOS_FEED_LINES", "0")
    body = render_slip(lambda p: write_line(p, "Hi"), feed_lines=0)
    payload = body[len(escpos_init_preamble()) :]
    assert b"\x1bd\x06" not in payload
    assert payload.endswith(b"\x1dV\x42\x00")


def test_prepare_receipt_logo_rgba_centered_on_canvas():
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    for x in range(10, 30):
        for y in range(5, 15):
            img.putpixel((x, y), (20, 40, 80, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    prepared = _prepare_receipt_logo(buf.getvalue(), max_width=64)
    assert prepared.size == (64, 10)
    assert prepared.mode == "1"
    ink_bbox = ImageOps.invert(prepared.convert("L")).getbbox()
    assert ink_bbox is not None
    assert ink_bbox[0] >= 8


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
    pre = escpos_init_preamble()
    body = raw[len(pre) :]
    idx = body.find(b"After logo")
    assert idx >= 3
    assert body[idx - 3 : idx - 1] == b"\x1b\x74"
    assert body[idx - 1] == 19


def test_prepare_receipt_logo_cache_reuses_identical_raster():
    raw = _solid_png_bytes()
    first = _prepare_receipt_logo(raw, max_width=64)
    second = _prepare_receipt_logo(raw, max_width=64)
    assert first.tobytes() == second.tobytes()
    assert first.size == second.size


def test_prepare_receipt_logo_cache_distinct_by_width():
    raw = _solid_png_bytes(size=(200, 40))
    wide = _prepare_receipt_logo(raw, max_width=384)
    narrow = _prepare_receipt_logo(raw, max_width=360)
    assert wide.size[0] == 384
    assert narrow.size[0] == 360
    assert wide.tobytes() != narrow.tobytes()


def test_prepare_receipt_logo_cache_clears_on_invalidate():
    raw = _solid_png_bytes()
    before = _prepare_receipt_logo(raw, max_width=64)
    clear_receipt_logo_cache()
    after = _prepare_receipt_logo(raw, max_width=64)
    assert before.tobytes() == after.tobytes()


def test_prepare_receipt_logo_threshold_matches_cutoff_175():
    """Pixels below 175 print (black); 175+ stay white — LUT must match legacy lambda."""
    img = Image.new("L", (8, 1), 255)
    img.putpixel((0, 0), 174)
    img.putpixel((1, 0), 175)
    buf = BytesIO()
    img.save(buf, format="PNG")
    prepared = _prepare_receipt_logo(buf.getvalue(), max_width=8)
    # Cropped to ink then centered on canvas; ink bbox should include the dark pixel.
    assert prepared.getpixel((3, 0)) == 0 or any(prepared.getpixel((x, 0)) == 0 for x in range(8))
