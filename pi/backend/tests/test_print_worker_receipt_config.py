"""Receipt builders honour event printing configuration."""

import re

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


def test_station_receipt_uses_label_not_name():
    ev = _event_with_printing()
    raw = build_escpos_receipt_text(
        {
            "table_number": 5,
            "lines": [{"article_id": 1, "qty": 1}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Brauerei Hell 0.5l", "label": "Hell 0.5", "price": 4.5}},
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Hell 0.5" in text
    assert "Brauerei Hell" not in text


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


def _schnitzel_ketchup_arts():
    return {
        "10": {
            "id": 10,
            "name": "Schnitzel",
            "price": 9.5,
            "additions": [{"article_id": 30, "name": "Ketchup", "price": 0.5}],
        },
        "30": {"id": 30, "name": "Ketchup", "price": 0.5},
    }


def test_customer_pickup_shows_addition_prices_when_enabled():
    ev = _event_with_printing(customer_receipt={"show_price": True})
    raw = build_customer_pickup_text(
        {
            "pickup_code": "C9",
            "lines": [
                {
                    "article_id": 10,
                    "qty": 1,
                    "additions": [{"article_id": 30, "qty": 1, "unit_cents": 50}],
                }
            ],
        },
        "Event",
        articles=_schnitzel_ketchup_arts(),
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "+ Ketchup" in text
    assert "9.50" in text
    assert "0.50" in text
    assert "10.00" not in text.split("+ Ketchup")[0]


def test_payment_receipt_shows_base_and_addition_without_double_count():
    raw = build_payment_receipt_text(
        {
            "lines": [
                {
                    "article_id": 10,
                    "qty": 1,
                    "additions": [{"article_id": 30, "qty": 1, "unit_cents": 50}],
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 1000}],
        },
        "Event",
        articles=_schnitzel_ketchup_arts(),
        currency="CHF",
    )
    text = raw.decode("cp858", errors="replace")
    assert "+ Ketchup" in text
    assert "9.50" in text
    assert "0.50" in text
    schnitzel_row = text.split("+ Ketchup")[0]
    assert "10.00" not in schnitzel_row


def test_payment_receipt_discounted_line_shows_combined_price_only():
    raw = build_payment_receipt_text(
        {
            "lines": [
                {
                    "article_id": 10,
                    "qty": 1,
                    "discount": {"kind": "percent", "value": 10},
                    "additions": [{"article_id": 30, "qty": 1, "unit_cents": 50}],
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 900}],
        },
        "Event",
        articles=_schnitzel_ketchup_arts(),
        currency="CHF",
    )
    text = raw.decode("cp858", errors="replace")
    assert "+ Ketchup" in text
    assert "9.00" in text
    assert "0.50" not in text


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
    idx = raw.find(b"Tom Keller")
    assert idx >= 0
    waiter_window = raw[max(0, idx - 12) : idx]
    assert b"\x1bM\x01" in waiter_window
    assert b"\x1b!\x30" not in waiter_window
    assert b"\x1bE\x01" not in waiter_window


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


def test_payment_receipt_addition_omits_qty_one():
    arts = {
        "10": {
            "id": 10,
            "name": "Schnitzel",
            "price": 9.5,
            "additions": [{"article_id": 30, "name": "Ketchup", "price": 0.5}],
        },
        "30": {"id": 30, "name": "Ketchup", "price": 0.5},
    }
    raw = build_payment_receipt_text(
        {
            "lines": [
                {
                    "article_id": 10,
                    "qty": 1,
                    "additions": [{"article_id": 30, "qty": 1, "unit_cents": 50}],
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 1000}],
        },
        "Event",
        articles=arts,
        currency="CHF",
    )
    text = raw.decode("cp858", errors="replace")
    assert "+ Ketchup" in text
    assert "1x Ketchup" not in text


def test_payment_receipt_addition_shows_qty_when_greater_than_one():
    arts = {
        "10": {
            "id": 10,
            "name": "Schnitzel",
            "price": 9.5,
            "additions": [{"article_id": 30, "name": "Ketchup", "price": 0.5}],
        },
        "30": {"id": 30, "name": "Ketchup", "price": 0.5},
    }
    raw = build_payment_receipt_text(
        {
            "lines": [
                {
                    "article_id": 10,
                    "qty": 1,
                    "additions": [{"article_id": 30, "qty": 2, "unit_cents": 50}],
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 1050}],
        },
        "Event",
        articles=arts,
        currency="CHF",
    )
    text = raw.decode("cp858", errors="replace")
    assert "+ 2x Ketchup" in text


def _payment_receipt_sample():
    return build_payment_receipt_text(
        {
            "table_number": 4,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
            "payments": [{"type": "cash", "amount_cents": 500}],
            "paid_at": "2026-06-01T12:00:00+00:00",
        },
        "Event",
        payment_id=99,
        articles={"1": {"id": 1, "name": "Bier", "price": 5.0}},
        currency="CHF",
    )


def test_payment_receipt_currency_only_on_total():
    raw = _payment_receipt_sample()
    text = raw.decode("cp858", errors="replace")
    assert "Total CHF:" in text
    assert "5.00 CHF" not in text
    assert "CHF 5.00" not in text
    for ln in text.splitlines():
        if ln.startswith("1x ") or ln.startswith("Bar:"):
            assert "CHF" not in ln


def test_payment_receipt_payment_line_right_aligned():
    def strip_esc(s: str) -> str:
        cleaned = re.sub(r"\x1b[@-Z\\-_]|\x1b\[[0-?]*[ -/]*[@-~]", "", s)
        return "".join(c for c in cleaned if c.isprintable() or c in " \t\n\r")

    raw = _payment_receipt_sample()
    text = strip_esc(raw.decode("cp858", errors="replace"))
    total_line = next(ln for ln in text.splitlines() if "Total CHF:" in ln)
    bar_line = next(ln for ln in text.splitlines() if ln.startswith("Bar:"))
    total_match = re.search(r"\d+\.\d{2}\s*$", total_line)
    bar_match = re.search(r"\d+\.\d{2}\s*$", bar_line)
    assert total_match and bar_match
    assert len(total_line) == len(bar_line)
    assert total_match.start() == bar_match.start()


def test_payment_receipt_total_line_bold():
    raw = _payment_receipt_sample()
    marker = b"Total CHF:"
    idx = raw.find(marker)
    assert idx >= 0
    assert b"\x1bE\x01" in raw[max(0, idx - 8):idx]


def test_station_receipt_hides_line_discount_hint():
    ev = _event_with_printing()
    raw = build_escpos_receipt_text(
        {
            "table_number": 3,
            "lines": [
                {
                    "article_id": 1,
                    "qty": 2,
                    "article_name": "Bier",
                    "discount": {"kind": "percent", "value": 10},
                }
            ],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 5.0}},
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Rabatt" not in text
    assert "2x Bier" in text or "2 Bier" in text


def test_payment_receipt_shows_line_discount():
    ev = _event_with_printing()
    raw = build_payment_receipt_text(
        {
            "lines": [
                {
                    "article_id": 1,
                    "qty": 2,
                    "article_name": "Bier",
                    "discount": {"kind": "percent", "value": 10},
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 900}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 5.0}},
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Rabatt 10%" in text
    assert "9.00" in text
    assert "Total CHF:" in text


def test_payment_receipt_shows_order_discount_and_voucher():
    ev = _event_with_printing()
    ev["discounts_enabled"] = True
    ev["configuration"] = ev.get("configuration") or {}
    ev["configuration"]["voucher_definitions"] = [
        {
            "uuid": "vd-20",
            "name": "20 CHF Gutschein",
            "kind": "fixed_amount",
            "value_cents": 2000,
            "allowed_article_ids": [],
            "include_additions": True,
        }
    ]
    raw = build_payment_receipt_text(
        {
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
            "order_discount": {"kind": "amount", "value": 100},
            "voucher_redemptions": [
                {"voucher_definition_uuid": "vd-20", "kind": "fixed_amount", "applied_cents": 400}
            ],
            "voucher_credit_cents": 400,
            "payments": [{"type": "cash", "amount_cents": 0}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 5.0}},
        currency="CHF",
        event=ev,
    )
    text = raw.decode("cp858", errors="replace")
    assert "Rabatt Bestellung" in text
    assert "Gutschein 20 CHF Gutschein" in text
    assert "Total CHF:" in text
    assert "0.00" in text
    assert "Gutschein:" in text
    assert "4.00" in text
    assert "10.00" not in text.split("Total CHF:")[-1].split("Bar:")[0]
