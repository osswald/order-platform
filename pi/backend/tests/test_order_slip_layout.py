"""Station order slip ESC/POS layout."""

from app.print_worker import _format_ordered_at, build_escpos_receipt_text


def _slip_text(slip: bytes) -> str:
    return slip.decode("cp858", errors="replace")


def test_format_ordered_at_europe_zurich(monkeypatch):
    monkeypatch.setenv("ESCPOS_TIMEZONE", "Europe/Zurich")
    assert _format_ordered_at("2024-01-22T10:07:00+00:00") == "22.01.2024 11:07 Uhr"


def test_table_order_slip_layout():
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
    )
    text = _slip_text(slip)
    assert "7" in text
    assert "Sommerfest" in text
    assert "22.01.2024 11:07 Uhr" in text
    assert "Station: Grill" in text
    assert "Best #00042" in text
    assert "Bon #000123" in text
    assert "Danke für Ihre Bestellung!" in text
    assert "Anna Müller" in text
    assert "10.50" in text
    assert "CHF" in text
    assert "+ Ketchup" in text


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
    )
    text = _slip_text(slip)
    assert "A17" in text
    assert text.index("A17") < text.index("Danke")
