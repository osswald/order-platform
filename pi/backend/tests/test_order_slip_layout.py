"""Station order slip ESC/POS layout."""

from app.print_worker import _format_ordered_at, build_escpos_receipt_text


def _slip_text(slip: bytes) -> str:
    return slip.decode("cp858", errors="replace")


def _event_with_printing(**profile_overrides):
    station = {
        "logo_enabled": False,
        "size_table_or_pickup": "xlarge",
        "size_order_lines": "large",
    }
    station.update(profile_overrides.get("station_receipt") or {})
    return {
        "configuration": {
            "printing": {
                "station_receipt": station,
            }
        }
    }


def test_format_ordered_at_europe_zurich(monkeypatch):
    monkeypatch.setenv("ESCPOS_TIMEZONE", "Europe/Zurich")
    assert _format_ordered_at("2024-01-22T10:07:00+00:00") == "22.01.2024 11:07 Uhr"


def test_table_order_slip_layout(monkeypatch):
    monkeypatch.setenv("ESCPOS_HERO_SCALE", "8")
    slip = build_escpos_receipt_text(
        {
            "table_number": 7,
            "order_number": 42,
            "ordered_at": "2024-01-22T10:07:00+00:00",
            "waiter_name": "Anna Müller",
            "lines": [
                {
                    "article_id": 10,
                    "qty": 3,
                    "article_name": "Bier 0.5",
                    "note": "warm",
                    "additions": [],
                },
                {
                    "article_id": 20,
                    "qty": 1,
                    "article_name": "Schnitzel",
                    "note": "",
                    "additions": [
                        {"article_id": 30, "qty": 1, "name": "Ketchup", "unit_cents": 50}
                    ],
                },
            ],
        },
        "Sommerfest",
        station_name="Grill",
        articles={
            "10": {"id": 10, "name": "Bier 0.5", "price": 3.5},
            "20": {"id": 20, "name": "Schnitzel", "price": 9.5},
        },
        local_order_id=123,
        currency="CHF",
        event=_event_with_printing(),
    )
    # GS ! scale 8 → n = 0x77
    assert bytes([0x1D, 0x21, 0x77]) in slip
    text = _slip_text(slip)
    assert "7" in text
    assert "Sommerfest" in text
    assert "22.01.2024 11:07 Uhr" in text
    assert "Station: Grill" in text
    assert "Best #00042" in text
    assert "Bon #000123" in text
    assert "Danke für Ihre Bestellung!" in text
    assert "Anna Müller" in text
    assert "10.50" not in text
    assert "CHF" not in text
    assert "3 Bier 0.5" in text or "3x Bier 0.5" in text
    assert "+ Ketchup" in text


def test_station_slip_order_lines_use_double_size():
    slip = build_escpos_receipt_text(
        {
            "table_number": 8,
            "order_number": 46,
            "ordered_at": "2026-05-29T18:26:00+00:00",
            "waiter_name": "Test",
            "lines": [{"article_id": 10, "qty": 1, "article_name": "Raclette", "additions": []}],
        },
        "Event",
        station_name="Küche",
        articles={"10": {"id": 10, "name": "Raclette", "price": 13.5}},
        local_order_id=82,
        event=_event_with_printing(station_receipt={"size_order_lines": "normal"}),
    )
    assert b"\x1b!\x30" in slip
    assert _slip_text(slip).count("Raclette") >= 1


def test_station_slip_always_double_size_even_when_config_normal():
    slip = build_escpos_receipt_text(
        {
            "table_number": 1,
            "lines": [{"article_id": 10, "qty": 1, "article_name": "Bier", "additions": []}],
        },
        "Event",
        articles={"10": {"id": 10, "name": "Bier", "price": 3.0}},
        event=_event_with_printing(
            station_receipt={
                "size_order_lines": "normal",
                "size_table_or_pickup": "normal",
            }
        ),
    )
    assert b"\x1b!\x30" in slip
    assert "Bier" in _slip_text(slip)


def test_pickup_order_slip_large_code():
    slip = build_escpos_receipt_text(
        {
            "table_number": 0,
            "pickup_code": "A17",
            "order_number": 1,
            "ordered_at": "2024-01-22T10:07:00+00:00",
            "waiter_name": "Kasse",
            "lines": [{"article_id": 10, "qty": 1, "article_name": "Menu", "additions": []}],
        },
        "Event",
        station_name="Theke",
        articles={"10": {"id": 10, "name": "Menu", "price": 12.0}},
        local_order_id=5,
        event=_event_with_printing(),
    )
    text = _slip_text(slip)
    assert "A17" in text
    assert text.index("A17") < text.index("Danke")
