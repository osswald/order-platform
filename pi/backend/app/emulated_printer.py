"""Store ESC/POS payloads as emulated receipts instead of sending to a printer."""

from __future__ import annotations

import base64
import os
import re

from sqlalchemy.orm import Session

from .models import EmulatedReceipt

# ESC sequences with a single parameter byte (total 3 bytes).
_ESC_ONE_PARAM = frozenset(
    {
        0x21,  # select print mode
        0x45,  # bold
        0x61,  # justification
        0x74,  # code page
        0x4D,  # font
        0x2D,  # underline
        0x64,  # feed n lines
    }
)

# GS sequences with a single parameter byte (total 3 bytes).
_GS_ONE_PARAM = frozenset({0x21})  # character size


def _escpos_skip_length(data: bytes, i: int) -> int:
    """Return number of bytes to skip starting at ESC (0x1B) or GS (0x1D)."""
    if i >= len(data):
        return 0
    prefix = data[i]
    if prefix not in (0x1B, 0x1D) or i + 1 >= len(data):
        return 1

    cmd = data[i + 1]

    if prefix == 0x1B:
        if cmd == 0x40:  # initialize
            return 2
        if cmd in _ESC_ONE_PARAM:
            return 3 if i + 2 < len(data) else 2
        return 2

    # GS (0x1D)
    if cmd == 0x21:  # character size
        return 3 if i + 2 < len(data) else 2
    if cmd == 0x56:  # cut
        return 4 if i + 3 < len(data) else min(3, len(data) - i)
    if cmd == 0x28 and i + 2 < len(data) and data[i + 2] == 0x4B:
        # GS ( k — raster image; pL/pH at bytes 3–4, then payload
        if i + 4 < len(data):
            payload_len = data[i + 3] + (data[i + 4] << 8)
            return min(5 + payload_len, len(data) - i)
        return 3
    if cmd == 0x76 and i + 2 < len(data) and data[i + 2] == 0x30:
        # GS v 0 — bit image raster; xL/xH yL/yH at bytes 3–6
        if i + 6 < len(data):
            width = data[i + 4] + (data[i + 5] << 8)
            height = data[i + 6] + (data[i + 7] << 8) if i + 7 < len(data) else 0
            raster_bytes = ((width + 7) // 8) * height
            return min(8 + raster_bytes, len(data) - i)
        return 3

    return 2


def escpos_bytes_to_preview(data: bytes) -> str:
    """Best-effort text extraction from ESC/POS bytes for UI preview."""
    cleaned = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b in (0x1B, 0x1D):
            i += _escpos_skip_length(data, i)
            continue
        if b in (0x0A, 0x0D) or b >= 0x20:
            cleaned.append(b)
        i += 1
    try:
        text = bytes(cleaned).decode("cp858", errors="replace")
    except Exception:
        text = bytes(cleaned).decode("latin-1", errors="replace")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_emulated_printer_mode() -> bool:
    return os.getenv("PRINTER_MODE", "").strip().lower() == "emulated"


def store_emulated_receipt(
    db: Session,
    *,
    data: bytes,
    job_kind: str | None = None,
    station_name: str | None = None,
) -> EmulatedReceipt:
    row = EmulatedReceipt(
        job_kind=job_kind,
        station_name=station_name,
        escpos_payload=base64.b64encode(data).decode("ascii"),
        preview_text=escpos_bytes_to_preview(data),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
