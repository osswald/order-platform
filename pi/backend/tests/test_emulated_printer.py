"""Emulated printer mode stores receipts instead of opening TCP."""

import asyncio
import base64

import pytest
from sqlalchemy.orm import Session

from app.emulated_printer import escpos_bytes_to_preview, is_emulated_printer_mode, store_emulated_receipt
from app.models import EmulatedReceipt
from app.print_worker import _send_to_printer


@pytest.fixture
def emulated_mode(monkeypatch):
    monkeypatch.setenv("PRINTER_MODE", "emulated")


def test_escpos_bytes_to_preview_strips_control_codes():
    data = b"\x1b@\x1b!\x00Hello\nWorld\n"
    preview = escpos_bytes_to_preview(data)
    assert "Hello" in preview
    assert "World" in preview


def test_escpos_bytes_to_preview_strips_sized_line_prefix():
    data = b"\x1b!\x301x Schweinsbratwurst\n"
    assert escpos_bytes_to_preview(data) == "1x Schweinsbratwurst"


def test_escpos_bytes_to_preview_strips_hero_scale_prefix():
    data = b"\x1d!\x77PICKUP 42\n\x1d!\x00"
    preview = escpos_bytes_to_preview(data)
    assert "PICKUP 42" in preview
    assert "w" not in preview


def test_escpos_bytes_to_preview_strips_cut_command():
    data = b"Thank you\n\x1dV\x42\x00"
    assert escpos_bytes_to_preview(data) == "Thank you"


def test_send_to_printer_stores_emulated_receipt(emulated_mode, db_session: Session):
    assert is_emulated_printer_mode()

    async def _run():
        await _send_to_printer(
            "emulated",
            0,
            b"Test receipt\n",
            db=db_session,
            job_kind="station_order",
            station_name="Bar",
        )

    asyncio.run(_run())
    rows = db_session.query(EmulatedReceipt).all()
    assert len(rows) == 1
    assert rows[0].station_name == "Bar"
    assert rows[0].job_kind == "station_order"
    assert base64.b64decode(rows[0].escpos_payload) == b"Test receipt\n"
