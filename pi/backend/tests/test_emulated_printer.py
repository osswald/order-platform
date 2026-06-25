"""Emulated printer mode stores receipts instead of opening TCP."""

import asyncio
import base64

import pytest
from app.emulated_printer import (
    escpos_bytes_to_preview,
    escpos_bytes_to_preview_lines,
    is_emulated_printer_mode,
)
from app.models import EmulatedReceipt
from app.print_worker import _send_to_printer, build_escpos_station_test_slip
from sqlalchemy.orm import Session


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


def test_preview_lines_large_order_line():
    data = b"\x1b!\x301x Schweinsbratwurst\n"
    lines = escpos_bytes_to_preview_lines(data)
    assert len(lines) == 1
    assert lines[0]["text"] == "1x Schweinsbratwurst"
    assert lines[0]["size"] == "large"
    assert lines[0]["align"] == "left"
    assert lines[0]["kind"] == "text"


def test_preview_lines_hero_pickup_centered_xlarge():
    data = b"\x1b\x61\x01\x1d!\x77PICKUP 42\n\x1d!\x00"
    lines = escpos_bytes_to_preview_lines(data)
    assert len(lines) == 1
    assert lines[0]["text"] == "PICKUP 42"
    assert lines[0]["align"] == "center"
    assert lines[0]["size"] == "xlarge"
    assert lines[0]["scale"] == 8


def test_preview_lines_small_centered_footer():
    data = b"\x1b\x61\x01\x1bM\x01Kellner Name\n"
    lines = escpos_bytes_to_preview_lines(data)
    assert len(lines) == 1
    assert lines[0]["text"] == "Kellner Name"
    assert lines[0]["align"] == "center"
    assert lines[0]["size"] == "small"


def test_preview_lines_logo_placeholder():
    data = b"Header\n\x1d\x76\x30\x00\x08\x00\x01\x00\x00\x00Footer\n"
    lines = escpos_bytes_to_preview_lines(data)
    assert lines[0]["text"] == "Header"
    logo = next(line for line in lines if line["kind"] == "logo")
    assert logo["align"] == "center"
    assert lines[-1]["text"] == "Footer"


def test_preview_lines_from_station_slip(monkeypatch):
    monkeypatch.setenv("ESCPOS_HERO_SCALE", "8")
    slip = build_escpos_station_test_slip(
        {
            "table_number": 1,
            "waiter_name": "Testdruck",
            "ordered_at": "2026-01-01T12:00:00Z",
            "lines": [
                {
                    "article_id": 1,
                    "qty": 1,
                    "article_name": "Bier",
                    "note": "Größe / Crème brûlée",
                    "additions": [],
                }
            ],
        },
        "Event Demo",
        station_name="Grill",
        articles={"1": {"id": 1, "name": "Bier", "price": 4.0}},
        event={
            "configuration": {
                "printing": {
                    "station_receipt": {
                        "logo_enabled": False,
                        "size_table_or_pickup": "xlarge",
                        "size_order_lines": "large",
                    }
                }
            }
        },
    )
    lines = escpos_bytes_to_preview_lines(slip)
    text_lines = [line for line in lines if line["kind"] == "text" and line["text"]]
    sizes = {line["size"] for line in text_lines}
    assert "xlarge" in sizes
    assert "large" in sizes
    hero = next(line for line in text_lines if line["text"].strip() == "1" and line["size"] == "xlarge")
    assert hero["align"] == "center"
    assert hero["scale"] == 8
    bier = next(line for line in text_lines if "Bier" in line["text"])
    assert bier["size"] == "large"


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
