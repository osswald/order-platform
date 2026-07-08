"""ESC/POS cash drawer kick presets."""

import pytest
from app.escpos_render import build_cash_drawer_kick, escpos_init_preamble


def test_build_cash_drawer_kick_escp_pin2():
    raw = build_cash_drawer_kick("escp_pin2")
    assert raw.startswith(escpos_init_preamble())
    assert raw.endswith(bytes.fromhex("1b70003232"))


def test_build_cash_drawer_kick_escp_pin5():
    raw = build_cash_drawer_kick("escp_pin5")
    assert raw.endswith(bytes.fromhex("1b70013232"))


def test_build_cash_drawer_kick_escp_pin2_long():
    raw = build_cash_drawer_kick("escp_pin2_long")
    assert raw.endswith(bytes.fromhex("1b700019fa"))


def test_build_cash_drawer_kick_escp_pin5_long():
    raw = build_cash_drawer_kick("escp_pin5_long")
    assert raw.endswith(bytes.fromhex("1b700119fa"))


def test_build_cash_drawer_kick_none_returns_empty():
    assert build_cash_drawer_kick("none") == b""
    assert build_cash_drawer_kick("") == b""


def test_build_cash_drawer_kick_unknown_raises():
    with pytest.raises(ValueError, match="unknown cash drawer command"):
        build_cash_drawer_kick("invalid")
