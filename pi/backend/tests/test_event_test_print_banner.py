"""TESTBETRIEB banner on slips when event status is test."""

from app.print_worker import (
    build_customer_pickup_text,
    build_escpos_receipt_text,
    build_payment_receipt_text,
    build_shift_close_receipt_text,
    build_voucher_slip_text,
)


def _slip_text(slip: bytes) -> str:
    return slip.decode("cp858", errors="replace")


def _event_with_status(status: str | None) -> dict:
    ev: dict = {
        "configuration": {
            "printing": {
                "station_receipt": {"logo_enabled": False},
                "customer_receipt": {"logo_enabled": False},
                "payment_receipt": {"logo_enabled": False},
            }
        }
    }
    if status is not None:
        ev["status"] = status
    return ev


def test_station_slip_shows_testbetrieb_for_test_event():
    raw = build_escpos_receipt_text(
        {
            "table_number": 5,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("test"),
    )
    assert "TESTBETRIEB" in _slip_text(raw)


def test_station_slip_hides_testbetrieb_for_prod_event():
    raw = build_escpos_receipt_text(
        {
            "table_number": 5,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("prod"),
    )
    assert "TESTBETRIEB" not in _slip_text(raw)


def test_station_slip_hides_testbetrieb_without_event():
    raw = build_escpos_receipt_text(
        {
            "table_number": 5,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=None,
    )
    assert "TESTBETRIEB" not in _slip_text(raw)


def test_pickup_slip_shows_testbetrieb_for_test_event():
    raw = build_customer_pickup_text(
        {
            "pickup_code": "C9",
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("test"),
    )
    assert "TESTBETRIEB" in _slip_text(raw)


def test_pickup_slip_hides_testbetrieb_for_prod_event():
    raw = build_customer_pickup_text(
        {
            "pickup_code": "C9",
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("prod"),
    )
    assert "TESTBETRIEB" not in _slip_text(raw)


def test_voucher_slip_shows_testbetrieb_for_test_event():
    raw = build_voucher_slip_text(
        event_name="Sommerfest",
        voucher_name="Gutschein 20",
        value_cents=2000,
        currency="CHF",
        event=_event_with_status("test"),
    )
    assert "TESTBETRIEB" in _slip_text(raw)


def test_voucher_slip_hides_testbetrieb_for_prod_event():
    raw = build_voucher_slip_text(
        event_name="Sommerfest",
        voucher_name="Gutschein 20",
        value_cents=2000,
        currency="CHF",
        event=_event_with_status("prod"),
    )
    assert "TESTBETRIEB" not in _slip_text(raw)


def test_payment_receipt_shows_testbetrieb_for_test_event():
    raw = build_payment_receipt_text(
        {
            "table_number": 1,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
            "payments": [{"type": "cash", "amount_cents": 450}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("test"),
    )
    assert "TESTBETRIEB" in _slip_text(raw)


def test_payment_receipt_hides_testbetrieb_for_prod_event():
    raw = build_payment_receipt_text(
        {
            "table_number": 1,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
            "payments": [{"type": "cash", "amount_cents": 450}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("prod"),
    )
    assert "TESTBETRIEB" not in _slip_text(raw)


def test_shift_close_shows_testbetrieb_for_test_event():
    raw = build_shift_close_receipt_text(
        {
            "subject_name": "Anna",
            "opening_balance_cents": 5000,
            "counted_cash_cents": 6000,
            "payments_by_method": {"cash": 1000},
            "vouchers_by_definition": {},
        },
        "Fest",
        currency="CHF",
        event=_event_with_status("test"),
    )
    assert "TESTBETRIEB" in _slip_text(raw)


def test_shift_close_hides_testbetrieb_for_prod_event():
    raw = build_shift_close_receipt_text(
        {
            "subject_name": "Anna",
            "opening_balance_cents": 5000,
            "counted_cash_cents": 6000,
            "payments_by_method": {"cash": 1000},
            "vouchers_by_definition": {},
        },
        "Fest",
        currency="CHF",
        event=_event_with_status("prod"),
    )
    assert "TESTBETRIEB" not in _slip_text(raw)


def test_testbetrieb_banner_is_case_insensitive():
    raw = build_escpos_receipt_text(
        {
            "table_number": 5,
            "lines": [{"article_id": 1, "qty": 1, "article_name": "Bier"}],
        },
        "Event",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.5}},
        currency="CHF",
        event=_event_with_status("TEST"),
    )
    assert "TESTBETRIEB" in _slip_text(raw)
