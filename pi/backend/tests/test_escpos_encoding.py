"""ESC/POS PC858 encoding and Testdruck slip layout."""

from app.print_worker import (
    _escpos_init,
    _escpos_text,
    build_escpos_station_test_slip,
)


def test_escpos_text_uses_cp858_single_byte():
    for ch in ("ä", "é", "è", "î", "ç"):
        encoded = _escpos_text(ch)
        assert encoded == ch.encode("cp858")
        assert len(encoded) == 1


def test_escpos_init_selects_code_page():
    buf = _escpos_init()
    assert buf.startswith(b"\x1b\x40")
    assert buf[2:4] == b"\x1b\x74"
    assert buf[4] == 19


def test_station_test_slip_has_center_align_and_font_commands():
    slip = build_escpos_station_test_slip(
        {
            "waiter_name": "Testdruck",
            "ordered_at": "2026-01-01T12:00:00Z",
            "lines": [
                {
                    "article_id": 1,
                    "qty": 1,
                    "article_name": "Bier",
                    "note": "Größe / Crème brûlée",
                    "additions": [],
                }
            ],
        },
        "Event Demo",
        station_name="Grill",
        articles={},
    )
    assert b"\x1b\x61\x01" in slip
    assert b"\x1b!\x30" in slip
    assert b"\x1b!\x10" in slip
    assert b"\x1b!\x20" in slip
    assert _escpos_text("Ää Öö Üü ß  Éé Èè Îî Çç") in slip
    assert _escpos_text("Größe / Crème brûlée") in slip
