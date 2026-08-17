"""Customer-display screensaver bytes are downscaled for kiosk/WebView clients."""

from __future__ import annotations

import hashlib
from io import BytesIO

import pytest
from app.screensaver_store import store_screensaver_bytes, wipe_screensaver_store
from PIL import Image


@pytest.fixture()
def screensaver_tmpdir(tmp_path, monkeypatch):
    root = tmp_path / "screensaver"
    monkeypatch.setenv("SCREENSAVER_DIR", str(root))
    wipe_screensaver_store()
    return root


def _jpeg(size: tuple[int, int], color: tuple[int, int, int] = (40, 80, 120)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_display_bytes_shrink_oversized_jpeg(screensaver_tmpdir):
    from app.screensaver_display import DISPLAY_MAX_EDGE, jpeg_bytes_for_display

    raw = _jpeg((4000, 3000))
    out, mime = jpeg_bytes_for_display(raw)
    assert mime == "image/jpeg"
    img = Image.open(BytesIO(out))
    assert max(img.size) <= DISPLAY_MAX_EDGE
    assert img.size[0] / img.size[1] == pytest.approx(4000 / 3000, rel=0.02)
    assert len(out) < len(raw)


def test_display_bytes_leave_small_image(screensaver_tmpdir):
    from app.screensaver_display import jpeg_bytes_for_display

    raw = _jpeg((800, 600))
    out, mime = jpeg_bytes_for_display(raw)
    assert mime == "image/jpeg"
    img = Image.open(BytesIO(out))
    assert img.size == (800, 600)


def test_get_screensaver_serves_display_sized_jpeg(client, screensaver_tmpdir):
    raw = _jpeg((3200, 1800), (10, 20, 30))
    sha = hashlib.sha256(raw).hexdigest()
    store_screensaver_bytes(sha, raw)

    r = client.get(f"/v1/screensaver/{sha}")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/jpeg")
    img = Image.open(BytesIO(r.content))
    assert max(img.size) <= 1920
    assert img.size == (1920, 1080)


def test_get_screensaver_404_unknown(client, screensaver_tmpdir):
    wipe_screensaver_store()
    r = client.get("/v1/screensaver/" + "a" * 64)
    assert r.status_code == 404


def test_get_screensaver_cors_for_android_webview(client, screensaver_tmpdir):
    raw = _jpeg((640, 480))
    sha = hashlib.sha256(raw).hexdigest()
    store_screensaver_bytes(sha, raw)
    r = client.get(
        f"/v1/screensaver/{sha}",
        headers={"Origin": "https://appassets.androidplatform.net"},
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "*"
