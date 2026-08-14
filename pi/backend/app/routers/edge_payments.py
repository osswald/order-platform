"""Register display and payment receipt routes."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..display_hub import display_hub
from ..models import PaymentReceipt, RegisterDisplayState
from ..print_worker import build_payment_receipt_text
from ..schemas.edge import (
    PaymentReceiptBody,
    PaymentReceiptEscposResponse,
    PaymentReceiptPrintBody,
    PaymentReceiptPrintResponse,
    PaymentsListResponse,
    RegisterDisplayBody,
    RegisterDisplayResponse,
)
from .edge_common import (
    _article_map,
    _create_payment_receipt_print_job,
    _line_totals,
    _payments_total_cents,
    _printer_host_configured,
)

router = APIRouter()


def _display_message(
    cash_register_uuid: str, event_id: int, payload: dict, updated_at: str | None
) -> dict:
    return {
        "cash_register_uuid": cash_register_uuid,
        "event_id": event_id,
        "payload": payload,
        "updated_at": updated_at,
    }


@router.get("/v1/registers/{cash_register_uuid}/display", response_model=RegisterDisplayResponse)
def get_register_display(
    cash_register_uuid: str, event_id: int = Query(...), db: Session = Depends(get_db)
) -> RegisterDisplayResponse:
    row = db.query(RegisterDisplayState).filter(RegisterDisplayState.cash_register_uuid == cash_register_uuid).first()
    if not row or int(row.event_id) != int(event_id):
        return RegisterDisplayResponse(
            cash_register_uuid=cash_register_uuid,
            event_id=event_id,
            payload={},
            updated_at=None,
        )
    return RegisterDisplayResponse(
        cash_register_uuid=cash_register_uuid,
        event_id=row.event_id,
        payload=json.loads(row.payload_json or "{}"),
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.put("/v1/registers/{cash_register_uuid}/display", response_model=RegisterDisplayResponse)
async def put_register_display(
    cash_register_uuid: str, body: RegisterDisplayBody, db: Session = Depends(get_db)
) -> RegisterDisplayResponse:
    row = db.query(RegisterDisplayState).filter(RegisterDisplayState.cash_register_uuid == cash_register_uuid).first()
    if not row:
        row = RegisterDisplayState(cash_register_uuid=cash_register_uuid, event_id=body.event_id)
        db.add(row)
    row.event_id = body.event_id
    row.payload_json = json.dumps(body.payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(row)
    payload = json.loads(row.payload_json or "{}")
    updated_at = row.updated_at.isoformat() if row.updated_at else None
    await display_hub.broadcast(
        cash_register_uuid,
        _display_message(cash_register_uuid, row.event_id, payload, updated_at),
    )
    return RegisterDisplayResponse(
        cash_register_uuid=cash_register_uuid,
        event_id=row.event_id,
        payload=payload,
        updated_at=updated_at,
    )


@router.websocket("/v1/registers/{cash_register_uuid}/display/ws")
async def register_display_ws(
    websocket: WebSocket,
    cash_register_uuid: str,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> None:
    await display_hub.connect(cash_register_uuid, websocket)
    try:
        row = (
            db.query(RegisterDisplayState)
            .filter(RegisterDisplayState.cash_register_uuid == cash_register_uuid)
            .first()
        )
        if row and int(row.event_id) == int(event_id):
            payload = json.loads(row.payload_json or "{}")
            updated_at = row.updated_at.isoformat() if row.updated_at else None
            await websocket.send_json(
                _display_message(cash_register_uuid, row.event_id, payload, updated_at)
            )
        else:
            await websocket.send_json(_display_message(cash_register_uuid, event_id, {}, None))
        while True:
            # Keep the socket open; clients do not need to send. Ignore inbound pings/text.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await display_hub.disconnect(cash_register_uuid, websocket)


@router.get("/v1/payments", response_model=PaymentsListResponse)
def list_payments(
    event_id: int = Query(...),
    waiter_uuid: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaymentsListResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    arts = _article_map(ev)
    q = db.query(PaymentReceipt).filter(PaymentReceipt.event_id == event_id)
    if waiter_uuid:
        q = q.filter(PaymentReceipt.waiter_uuid == waiter_uuid)
    rows = q.order_by(PaymentReceipt.id.desc()).limit(limit).all()
    payments = []
    for row in rows:
        payload = json.loads(row.payload_json or "{}")
        line_total, item_count = _line_totals(payload.get("lines") or [], arts)
        paid_total = _payments_total_cents(payload.get("payments") or []) or line_total
        payments.append(
            {
                "payment_id": row.id,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "paid_at": payload.get("paid_at") or payload.get("settled_at"),
                "table_number": payload.get("table_number") or payload.get("settlement_table"),
                "collective_bill_name": payload.get("collective_bill_name"),
                "order_number": payload.get("order_number"),
                "order_numbers": payload.get("order_numbers") or [],
                "waiter_name": payload.get("waiter_name"),
                "payment_types": [
                    str(p.get("type") or "")
                    for p in payload.get("payments") or []
                    if isinstance(p, dict) and p.get("type")
                ],
                "total_cents": paid_total,
                "item_count": item_count,
                "currency": ev.get("currency", "EUR"),
            }
        )
    return PaymentsListResponse(payments=payments)


@router.post("/v1/payments/{payment_id}/receipt", response_model=PaymentReceiptEscposResponse)
def payment_receipt(
    payment_id: int, body: PaymentReceiptBody | None = None, db: Session = Depends(get_db)
) -> PaymentReceiptEscposResponse:
    row = db.query(PaymentReceipt).filter(PaymentReceipt.id == payment_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, row.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    payload = json.loads(row.payload_json or "{}")
    esc = build_payment_receipt_text(
        payload,
        ev.get("name", "Event"),
        payment_id=row.id,
        articles=_article_map(ev),
        currency=ev.get("currency", "EUR"),
        reprint=bool(body and body.reprint),
        generated_at=datetime.now(UTC).isoformat(),
        event=ev,
        paper_width=body.paper_width if body else None,
        charset=body.charset if body else None,
    )
    return PaymentReceiptEscposResponse(
        payment_id=row.id,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
    )


@router.post("/v1/payments/{payment_id}/receipt/print", response_model=PaymentReceiptPrintResponse)
def payment_receipt_print_to_station(
    payment_id: int,
    body: PaymentReceiptPrintBody,
    db: Session = Depends(get_db),
) -> PaymentReceiptPrintResponse:
    station_uuid = body.station_uuid.strip()
    if not station_uuid:
        raise HTTPException(status_code=422, detail="station_uuid required")
    row = db.query(PaymentReceipt).filter(PaymentReceipt.id == payment_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, row.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    if not _printer_host_configured(ev, station_uuid):
        raise HTTPException(
            status_code=422,
            detail="Kein Drucker für diese Station konfiguriert",
        )
    job_id = _create_payment_receipt_print_job(
        db, row, ev, station_uuid, reprint=bool(body.reprint)
    )
    db.commit()
    return PaymentReceiptPrintResponse(ok=True, print_job_id=job_id)
