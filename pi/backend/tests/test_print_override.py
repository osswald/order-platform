"""ESCPOS_PRINTER_HOST_OVERRIDE routing."""

import asyncio

from app.print_worker import _effective_printer_host, _send_to_printer


def test_effective_printer_host_uses_override(monkeypatch):
    monkeypatch.setenv("ESCPOS_PRINTER_HOST_OVERRIDE", "escpos-netprinter")
    assert _effective_printer_host("192.168.1.50") == "escpos-netprinter"


def test_effective_printer_host_without_override(monkeypatch):
    monkeypatch.delenv("ESCPOS_PRINTER_HOST_OVERRIDE", raising=False)
    assert _effective_printer_host("192.168.1.50") == "192.168.1.50"


def test_send_to_printer_uses_override_host(monkeypatch, mock_printer_tcp):
    monkeypatch.setenv("ESCPOS_PRINTER_HOST_OVERRIDE", "escpos-netprinter")
    asyncio.run(_send_to_printer("192.168.1.50", 9100, b"\x1b\x40test"))
    assert mock_printer_tcp == [("escpos-netprinter", 9100)]
