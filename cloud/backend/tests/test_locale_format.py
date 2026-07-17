"""Tests for shared cloud locale formatting (Babel-backed)."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from app.locale_format import (
    format_amount,
    format_datetime,
    format_money,
    format_price_with_currency,
    format_time_label,
    intl_locale,
    resolve_format_locale,
)

FIXTURES_PATH = Path(__file__).resolve().parents[2] / "shared" / "format-fixtures.json"


@pytest.fixture
def fixtures() -> dict:
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def test_resolve_format_locale():
    assert resolve_format_locale("de", "CH") == "de_CH"
    assert resolve_format_locale("en", "CH") == "en_CH"
    assert resolve_format_locale("de", "DE") == "de_DE"
    assert resolve_format_locale("en", None) == "en_CH"


def test_intl_locale_bcp47_tags():
    assert intl_locale("de", "CH") == "de-CH"
    assert intl_locale("en", "DE") == "en-DE"


@pytest.mark.parametrize(
    ("cents", "country_code", "suffix"),
    [
        (0, "CH", "0.00"),
        (500, "CH", "5.00"),
        (1250, "CH", "12.50"),
    ],
)
def test_format_amount_swiss(cents, country_code, suffix):
    assert format_amount(cents, "de", country_code).endswith(suffix)


def test_format_amount_german_decimal_separator():
    assert format_amount(1250, "de", "DE") == "12,50"


def test_format_amount_large_swiss_uses_grouping(cents=123456):
    formatted = format_amount(cents, "de", "CH")
    assert formatted.endswith("234.56")
    assert "\u2019" in formatted or "'" in formatted


def test_format_money_prefixes_currency():
    assert format_money(1250, locale="de", currency="CHF", country_code="CH") == "CHF 12.50"
    assert format_money(1250, locale="de", currency="EUR", country_code="DE") == "EUR 12,50"


def test_format_price_with_currency():
    assert format_price_with_currency(12.5, "CHF", "de", "CH") == "CHF 12.50"


def test_format_datetime_swiss_pattern():
    dt = datetime(2026, 3, 1, 12, 5, tzinfo=ZoneInfo("Europe/Zurich"))
    assert format_datetime(dt, locale="de", country_code="CH") == "01.03.2026 12:05"


def test_format_time_label():
    dt = datetime(2026, 3, 1, 15, 30, tzinfo=ZoneInfo("Europe/Zurich"))
    assert format_time_label(dt, locale="de", country_code="CH") == "15:30"


def test_money_fixtures(fixtures):
    for case in fixtures["money"]:
        country = case.get("country_code")
        amount = format_amount(case["cents"], case["ui_locale"], country)
        money = format_money(
            case["cents"],
            locale=case["ui_locale"],
            currency=case["currency"],
            country_code=country,
        )
        if "expected_amount" in case:
            assert amount == case["expected_amount"]
        if "expected_money" in case:
            assert money == case["expected_money"]
        if "expected_amount_suffix" in case:
            assert amount.endswith(case["expected_amount_suffix"])
        if "expected_money_prefix" in case:
            assert money.startswith(case["expected_money_prefix"])


def test_format_locale_fixtures(fixtures):
    for case in fixtures["format_locale"]:
        assert resolve_format_locale(case["ui_locale"], case.get("country_code")) == case["babel_locale"]
        assert intl_locale(case["ui_locale"], case.get("country_code")) == case["intl_locale"]
