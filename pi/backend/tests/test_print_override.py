"""ESCPOS_PRINTER_HOST_OVERRIDE routing."""

import asyncio

from app.print_worker import _effective_printer_host, _send_to_printer

OVERRIDE_HOST = "192.168.1.99"


def test_effective_printer_host_uses_override(monkeypatch):
    monkeypatch.setenv("ESCPOS_PRINTER_HOST_OVERRIDE", OVERRIDE_HOST)
    assert _effective_printer_host("192.168.1.50") == OVERRIDE_HOST


def test_effective_printer_host_without_override(monkeypatch):
    monkeypatch.delenv("ESCPOS_PRINTER_HOST_OVERRIDE", raising=False)
    assert _effective_printer_host("192.168.1.50") == "192.168.1.50"


def test_send_to_printer_uses_override_host(monkeypatch, mock_printer_tcp):
    monkeypatch.setenv("ESCPOS_PRINTER_HOST_OVERRIDE", OVERRIDE_HOST)
    asyncio.run(_send_to_printer("192.168.1.50", 9100, b"\x1b\x40test"))
    assert mock_printer_tcp == [(OVERRIDE_HOST, 9100)]
