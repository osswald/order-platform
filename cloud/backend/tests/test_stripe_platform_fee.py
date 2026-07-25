"""Platform application fee on Terminal charges."""

import pytest
from app.stripe_client import DEFAULT_PLATFORM_FEE_BPS, platform_fee_bps, platform_fee_cents


def test_default_rate_is_20_bps():
    assert DEFAULT_PLATFORM_FEE_BPS == 20
    assert platform_fee_bps() == 20


@pytest.mark.parametrize(
    ("amount_cents", "expected"),
    [
        (1000, 2),  # CHF 10.00 -> 2 cents
        (10000, 20),  # CHF 100.00 -> 20 cents
        (250, 1),  # 0.5 cents rounds half-up
        (249, 0),  # 0.498 cents rounds down
        (100, 0),  # too small to charge a fee
        (1, 0),
        (0, 0),
    ],
)
def test_fee_rounds_half_up_to_the_nearest_cent(amount_cents, expected):
    assert platform_fee_cents(amount_cents) == expected


def test_fee_is_never_greater_than_or_equal_to_the_amount():
    assert platform_fee_cents(1000, bps=20000) < 1000


def test_rate_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("STRIPE_PLATFORM_FEE_BPS", "50")
    assert platform_fee_bps() == 50
    assert platform_fee_cents(1000) == 5


@pytest.mark.parametrize("value", ["", "   ", "not-a-number", "-5"])
def test_invalid_rate_falls_back_to_default(monkeypatch, value):
    monkeypatch.setenv("STRIPE_PLATFORM_FEE_BPS", value)
    assert platform_fee_bps() == DEFAULT_PLATFORM_FEE_BPS


def test_zero_rate_disables_the_fee(monkeypatch):
    monkeypatch.setenv("STRIPE_PLATFORM_FEE_BPS", "0")
    assert platform_fee_cents(10000) == 0
