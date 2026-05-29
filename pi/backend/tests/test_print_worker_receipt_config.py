"""Receipt builders honour event printing configuration."""

from app.print_worker import build_customer_pickup_text, build_escpos_receipt_text


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
    return {
        "configuration": {
            "printing": {
                "label_event_title": profile_overrides.get("label_event_title", ""),
                "station_receipt": station,
                "customer_receipt": customer,
            }
        }
    }


def test_station_receipt_custom_title_and_footer():
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
    text = raw.decode("latin-1", errors="replace")
    assert "Sommerfest" in text
    assert "Original Name" not in text
    assert "Danke!" in text
    assert "Guten Appetit" in text


def test_customer_receipt_custom_footer_overrides_legacy():
    ev = _event_with_printing(customer_receipt={"bottom_line": "Abholung Hinten"})
    raw = build_customer_pickup_text(
        {"lines": [{"article_id": 1, "qty": 1}], "pickup_code": "B7"},
        "Event",
        event=ev,
        articles={"1": {"name": "Snack"}},
    )
    text = raw.decode("latin-1", errors="replace")
    assert "Abholung Hinten" in text
    assert "Bitte an der Ausgabe abholen." not in text


def test_customer_receipt_legacy_footer_when_empty():
    ev = _event_with_printing()
    raw = build_customer_pickup_text(
        {"lines": [], "pickup_code": "X1"},
        "Event",
        event=ev,
    )
    text = raw.decode("latin-1", errors="replace")
    assert "Bitte an der Ausgabe abholen." in text
