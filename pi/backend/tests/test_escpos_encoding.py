"""ESC/POS PC858 encoding and Testdruck slip layout."""

from app.escpos_render import encode_escpos_text, escpos_init_preamble
from app.print_worker import build_escpos_station_test_slip


def test_escpos_text_uses_cp858_single_byte():
    for ch in ("ä", "é", "è", "î", "ç"):
        encoded = encode_escpos_text(ch)
        assert encoded == ch.encode("cp858")
        assert len(encoded) == 1


def test_escpos_init_selects_code_page():
    buf = escpos_init_preamble()
    assert buf.startswith(b"\x1b\x40")
    assert buf[2:4] == b"\x1b\x74"
    assert buf[4] == 19


def test_station_test_slip_has_center_align_and_accent_demo():
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
    text = slip.decode("cp858", errors="replace")
    assert b"\x1b\x61\x01" in slip
    assert "Ää Öö Üü ß  Éé Èè Îî Çç" in text
    assert "Größe / Crème brûlée" in text
    assert "Testdruck" in text
