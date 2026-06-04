"""Store ESC/POS payloads as emulated receipts instead of sending to a printer."""

from __future__ import annotations

import base64
import os
import re

from sqlalchemy.orm import Session

from .models import EmulatedReceipt


def is_emulated_printer_mode() -> bool:
    return os.getenv("PRINTER_MODE", "").strip().lower() == "emulated"


def escpos_bytes_to_preview(data: bytes) -> str:
    """Best-effort text extraction from ESC/POS bytes for UI preview."""
    cleaned = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0x1B and i + 1 < len(data):
            i += 2
            continue
        if b == 0x1D and i + 1 < len(data):
            i += 2
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
