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
