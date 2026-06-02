"""Receipt builders honour event printing configuration."""

from app.print_worker import build_customer_pickup_text, build_escpos_receipt_text, build_payment_receipt_text


def _event_with_printing(**profile_overrides):
    station = {
        "logo_enabled": False,
        "show_event_title": True,
        "size_table_or_pickup": "large",
        "size_order_lines": "normal",
        "show_price": False,
        "bottom_line": "",
    }
    customer = {
        "logo_enabled": False,
        "show_event_title": True,
        "size_table_or_pickup": "xlarge",
        "size_order_lines": "normal",
        "show_price": False,
        "bottom_line": "",
    }
    station.update(profile_overrides.get("station_receipt") or {})
    customer.update(profile_overrides.get("customer_receipt") or {})
    payment = {
        "logo_enabled": False,
        "show_event_title": True,
        "size_order_lines": "normal",
        "bottom_line": "",
    }
    payment.update(profile_overrides.get("payment_receipt") or {})
    return {
        "configuration": {
            "printing": {
                "label_event_title": profile_overrides.get("label_event_title", ""),
                "station_receipt": station,
                "customer_receipt": customer,
                "payment_receipt": payment,
            }
        }
    }


def test_station_receipt_never_shows_prices_when_profile_enabled():
    ev = _event_with_printing(
        station_receipt={"show_price": True},
        customer_receipt={"show_price": False},
    )
    raw = build_escpos_receipt_text(
        {
            "table_number": 5,
            "lines": [{"article_id": 1, "qty": 2, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "8.00" not in text
    assert "CHF" not in text
    assert "2x Bier" in text or "2 Bier" in text


def test_customer_pickup_shows_prices_and_total_when_enabled():
    ev = _event_with_printing(customer_receipt={"show_price": True})
    raw = build_customer_pickup_text(
        {
            "pickup_code": "C9",
            "lines": [{"article_id": 1, "qty": 2, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "9.00" in text
    assert "CHF" in text


def test_station_receipt_custom_title_no_footer():
    ev = _event_with_printing(
        label_event_title="Sommerfest",
        station_receipt={"bottom_line": "Danke!\nGuten Appetit"},
    )
    raw = build_escpos_receipt_text(
        {"lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}], "pickup_code": "A12"},
        "Original Name",
        event=ev,
        articles={"1": {"name": "Bier"}},
    )
    text = raw.decode("cp858", errors="replace")
    assert "Sommerfest" in text
    assert "Original Name" not in text
    assert "Danke!" not in text
    assert "Guten Appetit" not in text
    assert "Danke für Ihre Bestellung!" not in text


def test_station_receipt_shows_waiter_name():
    ev = _event_with_printing()
    raw = build_escpos_receipt_text(
        {
            "table_number": 3,
            "waiter_name": "Tom Keller",
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Wasser"}],
        },
        "Event",
        articles={"1": {"name": "Wasser"}},
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Tom Keller" in text


def test_station_receipt_prefers_cash_register_name():
    ev = _event_with_printing()
    raw = build_escpos_receipt_text(
        {
            "table_number": 0,
            "pickup_code": "B2",
            "order_source": "cash_register",
            "cash_register_name": "Hauptkasse",
            "waiter_name": "Tom Keller",
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Snack"}],
        },
        "Event",
        articles={"1": {"name": "Snack"}},
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Hauptkasse" in text
    assert "Tom Keller" not in text


def test_customer_receipt_custom_footer_overrides_legacy():
    ev = _event_with_printing(customer_receipt={"bottom_line": "Abholung Hinten"})
    raw = build_customer_pickup_text(
        {"lines": [{"article_id": 1, "qty": 1}], "pickup_code": "B7"},
        "Event",
        event=ev,
        articles={"1": {"name": "Snack"}},
    )
    text = raw.decode("cp858", errors="replace")
    assert "Abholung Hinten" in text
    assert "Bitte an der Ausgabe abholen." not in text
    assert "Station:" in text
    assert "Abholcode" in text
    assert "B7" in text


def test_customer_receipt_legacy_footer_when_empty():
    ev = _event_with_printing()
    raw = build_customer_pickup_text(
        {"lines": [], "pickup_code": "X1"},
        "Event",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Bitte an der Ausgabe abholen." in text


def test_payment_receipt_honours_profile():
    ev = _event_with_printing(
        label_event_title="Sommerfest",
        payment_receipt={
            "show_event_title": True,
            "bottom_line": "Vielen Dank",
        },
    )
    raw = build_payment_receipt_text(
        {
            "table_number": 4,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
            "payments": [{"type": "cash", "amount_cents": 500}],
            "paid_at": "2026-06-01T12:00:00+00:00",
        },
        "Original",
        payment_id=99,
        articles={"1": {"id": 1, "name": "Bier", "price": 5.0}},
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Sommerfest" in text
    assert "Original" not in text
    assert "Vielen Dank" in text
    assert "Danke!" not in text
    assert "Tisch: 4" in text


def test_payment_receipt_hides_event_title_and_uses_default_footer():
    ev = _event_with_printing(payment_receipt={"show_event_title": False, "bottom_line": ""})
    raw = build_payment_receipt_text(
        {"lines": [], "payments": [{"type": "cash", "amount_cents": 100}]},
        "Event Name",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Event Name" not in text
    assert "Danke!" in text
