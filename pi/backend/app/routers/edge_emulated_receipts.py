"""Pi emulated receipt routes."""

from __future__ import annotations

import base64
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import EmulatedReceipt

router = APIRouter()


class PreviewLine(BaseModel):
    text: str = ""
    align: Literal["left", "center", "right"] = "left"
    size: Literal["small", "normal", "large", "xlarge"] = "normal"
    scale: int | None = None
    bold: bool = False
    kind: Literal["text", "logo"] = "text"


class EmulatedReceiptSummary(BaseModel):
    id: int
    job_kind: str | None = None
    station_name: str | None = None
    preview_text: str
    preview_lines: list[PreviewLine] = []
    created_at: str | None = None


class EmulatedReceiptDetail(EmulatedReceiptSummary):
    escpos_payload: str


def _emulated_receipt_preview_lines(row: EmulatedReceipt) -> list[PreviewLine]:
    from ..emulated_printer import escpos_bytes_to_preview_lines

    try:
        raw = base64.b64decode(row.escpos_payload or "")
    except Exception:
        return []
    return [PreviewLine(**line) for line in escpos_bytes_to_preview_lines(raw)]


def _emulated_receipt_summary(row: EmulatedReceipt) -> EmulatedReceiptSummary:
    return EmulatedReceiptSummary(
        id=row.id,
        job_kind=row.job_kind,
        station_name=row.station_name,
        preview_text=row.preview_text or "",
        preview_lines=_emulated_receipt_preview_lines(row),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/v1/emulated-receipts", response_model=list[EmulatedReceiptSummary])
def list_emulated_receipts(db: Session = Depends(get_db)) -> list[EmulatedReceiptSummary]:
    from ..emulated_printer import is_emulated_printer_mode

    if not is_emulated_printer_mode():
        raise HTTPException(status_code=404, detail="Emulated printer mode is not enabled")
    rows = db.query(EmulatedReceipt).order_by(EmulatedReceipt.id.desc()).limit(100).all()
    return [_emulated_receipt_summary(row) for row in rows]


@router.get("/v1/emulated-receipts/{receipt_id}", response_model=EmulatedReceiptDetail)
def get_emulated_receipt(receipt_id: int, db: Session = Depends(get_db)) -> EmulatedReceiptDetail:
    from ..emulated_printer import is_emulated_printer_mode

    if not is_emulated_printer_mode():
        raise HTTPException(status_code=404, detail="Emulated printer mode is not enabled")
    row = db.query(EmulatedReceipt).filter(EmulatedReceipt.id == receipt_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Receipt not found")
    summary = _emulated_receipt_summary(row)
    return EmulatedReceiptDetail(
        **summary.model_dump(),
        escpos_payload=row.escpos_payload,
    )
