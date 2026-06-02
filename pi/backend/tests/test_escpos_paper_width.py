"""Receipt paper width presets for Bluetooth payment receipts."""

import re

from app.escpos_render import PAPER_WIDTH_PRESETS, resolve_line_width, resolve_logo_max_width
from app.print_worker import build_payment_receipt_text


def _decode_receipt(raw: bytes) -> str:
    return raw.decode("cp858", errors="replace")


def _strip_esc(text: str) -> str:
    cleaned = re.sub(r"\x1b[@-Z\\-_]|\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    return "".join(c for c in cleaned if c.isprintable() or c in " \t\n\r")


def _payload_with_long_item():
    return {
        "table_number": 7,
        "waiter_name": "Test",
        "lines": [
            {
                "article_id": 1,
                "qty": 1,
                "article_name": "Schweinsbratwurst mit viel Text",
                "additions": [],
            }
        ],
        "payments": [{"type": "cash", "amount_cents": 500}],
        "paid_at": "2026-06-01T14:06:00+00:00",
    }


def test_resolve_line_width_presets():
    assert resolve_line_width("80mm") == 48
    assert resolve_line_width("58mm") == 32
    assert resolve_line_width("53mm") == 30
    assert resolve_line_width(None) == resolve_line_width("")
    assert resolve_line_width("invalid") == resolve_line_width(None)


def test_resolve_logo_max_width_scales_with_line_width():
    assert resolve_logo_max_width(48) == 384
    assert resolve_logo_max_width(30) == 240


def test_payment_receipt_narrow_lines_fit_paper_width():
    arts = {"1": {"id": 1, "name": "Item", "price": 5.0, "additions": []}}
    raw_narrow = build_payment_receipt_text(
        _payload_with_long_item(),
        "Event",
        articles=arts,
        currency="CHF",
        paper_width="53mm",
    )
    raw_wide = build_payment_receipt_text(
        _payload_with_long_item(),
        "Event",
        articles=arts,
        currency="CHF",
        paper_width="80mm",
    )
    width_narrow = PAPER_WIDTH_PRESETS["53mm"]
    width_wide = PAPER_WIDTH_PRESETS["80mm"]

    narrow_text = _strip_esc(_decode_receipt(raw_narrow))
    wide_text = _strip_esc(_decode_receipt(raw_wide))
    narrow_seps = [ln for ln in narrow_text.splitlines() if ln and set(ln) == {"-"}]
    wide_seps = [ln for ln in wide_text.splitlines() if ln and set(ln) == {"-"}]
    assert narrow_seps
    assert wide_seps
    assert len(narrow_seps[0]) == width_narrow
    assert len(wide_seps[0]) == width_wide

    narrow_item_lines = [ln for ln in narrow_text.splitlines() if "CHF" in ln and "x " in ln]
    wide_item_lines = [ln for ln in wide_text.splitlines() if "CHF" in ln and "x " in ln]
    assert len(narrow_item_lines[0]) < len(wide_item_lines[0])
