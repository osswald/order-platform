"""ESC/POS charset encoding and Testdruck slip layout."""

from app.escpos_render import (
    RECEIPT_CHARSET_PRESETS,
    encode_escpos_text,
    escpos_init_preamble,
    render_slip,
    resolve_escpos_charset,
    transliterate_receipt_text,
    write_line,
)
from app.print_worker import build_escpos_station_test_slip, build_payment_receipt_text


def _assert_esc_t_before(body: bytes, needle: bytes, *, codepage: int) -> None:
    idx = body.find(needle)
    assert idx >= 3, f"{needle!r} not found in slip body"
    assert body[idx - 3 : idx - 1] == b"\x1b\x74"
    assert body[idx - 1] == codepage


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


def test_resolve_receipt_charset_presets():
    assert resolve_escpos_charset("pc858") == ("cp858", 19)
    assert resolve_escpos_charset("pc850") == ("cp850", 2)
    assert resolve_escpos_charset("cp1252") == ("cp1252", 16)
    assert resolve_escpos_charset("ascii") == ("ascii", 0)
    assert set(RECEIPT_CHARSET_PRESETS) == {"pc858", "pc850", "cp1252", "ascii"}


def test_encode_escpos_text_honors_charset_preset():
    assert encode_escpos_text("ä", charset="pc850") == "ä".encode("cp850")
    assert encode_escpos_text("ä", charset="cp1252") == "ä".encode("cp1252")


def test_write_escpos_text_prepends_esc_t_codepage():
    raw = render_slip(lambda p: write_line(p, "Hello"))
    pre = escpos_init_preamble()
    body = raw[len(pre) :]
    _assert_esc_t_before(body, b"Hello", codepage=19)


def test_render_slip_esc_t_before_each_text_line():
    def render(p):
        write_line(p, "Line one")
        write_line(p, "Line two")

    raw = render_slip(render, charset="pc850")
    pre = escpos_init_preamble(charset="pc850")
    body = raw[len(pre) :]
    _assert_esc_t_before(body, b"Line one", codepage=2)
    _assert_esc_t_before(body, b"Line two", codepage=2)


def test_render_slip_text_only_has_esc_t_before_text():
    """Regression: text-only slips must still select code page before each line."""
    raw = render_slip(lambda p: (write_line(p, "Testdruck"), write_line(p, "Danke")))
    pre = escpos_init_preamble()
    body = raw[len(pre) :]
    _assert_esc_t_before(body, b"Testdruck", codepage=19)
    _assert_esc_t_before(body, b"Danke", codepage=19)


def test_render_slip_body_avoids_esc_t_pc437_reset():
    raw = render_slip(lambda p: write_line(p, "Größe ä"))
    pre = escpos_init_preamble()
    body = raw[len(pre) :]
    assert b"\x1b\x74\x00" not in body
    assert "ä".encode("cp858") in body


def test_render_slip_pc850_charset():
    raw = render_slip(lambda p: write_line(p, "Größe"), charset="pc850")
    pre = escpos_init_preamble(charset="pc850")
    body = raw[len(pre) :]
    assert pre[4] == 2
    assert b"\x1b\x74\x00" not in body
    assert "ö".encode("cp850") in body


def test_station_test_slip_mirrors_production_sizes(monkeypatch):
    monkeypatch.setenv("ESCPOS_HERO_SCALE", "8")
    slip = build_escpos_station_test_slip(
        {
            "table_number": 1,
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
        articles={"1": {"id": 1, "name": "Bier", "price": 4.0}},
        event={
            "configuration": {
                "printing": {
                    "station_receipt": {
                        "logo_enabled": False,
                        "size_table_or_pickup": "xlarge",
                        "size_order_lines": "large",
                    }
                }
            }
        },
    )
    text = slip.decode("cp858", errors="replace")
    assert b"\x1b\x61\x01" in slip
    assert bytes([0x1D, 0x21, 0x77]) in slip
    idx = slip.find(b"Bier")
    assert idx >= 0
    window = slip[max(0, idx - 12) : idx + 12]
    assert b"\x1b!\x30" in window
    assert "Ää Öö Üü ß  Éé Èè Îî Çç" in text
    assert "Station: Grill" in text
    assert "Danke für Ihre Bestellung!" not in text
    assert "Testdruck" in text


def test_payment_receipt_test_charset_banner():
    slip = build_payment_receipt_text(
        {
            "table_number": 1,
            "waiter_name": "Test",
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier", "note": "", "additions": []}],
            "payments": [{"type": "cash", "amount_cents": 500}],
            "paid_at": "2026-01-01T12:00:00Z",
        },
        "Event Demo",
        currency="CHF",
        test_charset_banner=True,
    )
    text = slip.decode("cp858", errors="replace")
    assert "Ää Öö Üü ß  Éé Èè Îî Çç" in text


def test_transliterate_receipt_text_german():
    assert transliterate_receipt_text("Größe") == "Groesse"
    assert transliterate_receipt_text("Zürich") == "Zuerich"
    assert transliterate_receipt_text("Äpfel") == "Aepfel"
    assert transliterate_receipt_text("Straße") == "Strasse"
    assert transliterate_receipt_text("Crème brûlée") == "Creme brulee"


def test_encode_escpos_text_ascii_transliterates():
    assert encode_escpos_text("Größe", charset="ascii") == b"Groesse"
    assert encode_escpos_text("Zürich", charset="ascii") == b"Zuerich"


def test_render_slip_ascii_charset_transliterates():
    raw = render_slip(lambda p: write_line(p, "Zürich"), charset="ascii")
    pre = escpos_init_preamble(charset="ascii")
    body = raw[len(pre) :]
    assert b"Zuerich" in body
    _assert_esc_t_before(body, b"Zuerich", codepage=0)


def test_payment_receipt_charset_pc850():
    slip = build_payment_receipt_text(
        {
            "table_number": 1,
            "waiter_name": "Test",
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Größe", "note": "", "additions": []}],
            "payments": [{"type": "cash", "amount_cents": 500}],
            "paid_at": "2026-01-01T12:00:00Z",
        },
        "Event Demo",
        currency="CHF",
        charset="pc850",
    )
    pre = escpos_init_preamble(charset="pc850")
    body = slip[len(pre) :]
    assert b"\x1b\x74\x00" not in body
    assert "ö".encode("cp850") in body
