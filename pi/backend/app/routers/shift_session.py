"""Cash shift session API (Kellner-/Kassenabrechnung)."""

from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict_raw
from ..deps import get_db
from ..domain.cash_sessions import (
    close_session,
    get_open_session,
    open_session,
    session_to_sync_payload,
    shift_settlement_enabled,
)
from ..models import PrintJob
from ..print_worker import _send_to_printer, build_shift_close_receipt_text
from ..printer_endpoint import resolve_printer_endpoint
from ..schemas.edge import (
    ShiftSessionCloseBody,
    ShiftSessionEscposResponse,
    ShiftSessionOpenBody,
    ShiftSessionPrintResponse,
    ShiftSessionRead,
    ShiftSessionReceiptBody,
)
from ..shift_integration import session_to_api_dict, sync_cash_session

router = APIRouter()


def _require_shift_enabled(ev: dict) -> None:
    if not shift_settlement_enabled(ev):
        raise HTTPException(status_code=404, detail="Shift settlement not enabled for event")


@router.get("/v1/shift-session/active", response_model=ShiftSessionRead)
def shift_session_active(
    event_id: int = Query(...),
    subject_type: str = Query(...),
    waiter_uuid: str | None = Query(None),
    cash_register_uuid: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ShiftSessionRead:
    bundle = get_bundle_dict_raw(db) or {}
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    _require_shift_enabled(ev)
    session = get_open_session(
        db,
        event_id=event_id,
        subject_type=subject_type.strip().lower(),
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    if not session:
        raise HTTPException(status_code=404, detail="No open shift")
    return ShiftSessionRead(**session_to_api_dict(session))


@router.post("/v1/shift-session/open", response_model=ShiftSessionRead)
def shift_session_open(body: ShiftSessionOpenBody, db: Session = Depends(get_db)) -> ShiftSessionRead:
    bundle = get_bundle_dict_raw(db) or {}
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    _require_shift_enabled(ev)
    session = open_session(
        db,
        ev,
        event_id=body.event_id,
        subject_type=body.subject_type,
        opening_balance_cents=body.opening_balance_cents,
        waiter_uuid=body.waiter_uuid,
        cash_register_uuid=body.cash_register_uuid,
        operator_waiter_uuid=body.operator_waiter_uuid,
    )
    sync_cash_session(db, session)
    db.commit()
    db.refresh(session)
    return ShiftSessionRead(**session_to_api_dict(session))


@router.post("/v1/shift-session/{session_id}/close", response_model=ShiftSessionRead)
def shift_session_close(
    session_id: int,
    body: ShiftSessionCloseBody,
    db: Session = Depends(get_db),
) -> ShiftSessionRead:
    from ..models_operational import CashSession

    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Shift not found")
    bundle = get_bundle_dict_raw(db) or {}
    ev = event_from_bundle(bundle, session.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    _require_shift_enabled(ev)
    close_session(db, session, counted_cash_cents=body.counted_cash_cents)
    sync_cash_session(db, session)
    db.commit()
    db.refresh(session)
    return ShiftSessionRead(**session_to_api_dict(session))


def _shift_receipt_escpos(
    db: Session, session, ev: dict, *, paper_width: str | None, charset: str | None = None
) -> bytes:
    payload = session_to_sync_payload(db, session)
    return build_shift_close_receipt_text(
        payload,
        ev.get("name", "Event"),
        currency=ev.get("currency", "EUR"),
        event=ev,
        paper_width=paper_width,
        charset=charset,
    )


@router.post("/v1/shift-session/{session_id}/receipt", response_model=ShiftSessionEscposResponse)
def shift_session_receipt(
    session_id: int,
    body: ShiftSessionReceiptBody | None = None,
    db: Session = Depends(get_db),
) -> ShiftSessionEscposResponse:
    from ..models_operational import CashSession

    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Shift not found")
    bundle = get_bundle_dict_raw(db) or {}
    ev = event_from_bundle(bundle, session.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    if session.status == "OPEN" and body and body.counted_cash_cents is not None:
        close_session(db, session, counted_cash_cents=body.counted_cash_cents)
        sync_cash_session(db, session)
        db.commit()
        db.refresh(session)
    esc = _shift_receipt_escpos(
        db,
        session,
        ev,
        paper_width=body.paper_width if body else None,
        charset=body.charset if body else None,
    )
    return ShiftSessionEscposResponse(
        cash_session_id=int(session.id),
        escpos_payload=base64.b64encode(esc).decode("ascii"),
    )


@router.post("/v1/shift-session/{session_id}/print", response_model=ShiftSessionPrintResponse)
def shift_session_print(
    session_id: int,
    body: ShiftSessionCloseBody,
    db: Session = Depends(get_db),
) -> ShiftSessionPrintResponse:
    from ..models_operational import CashSession

    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Shift not found")
    bundle = get_bundle_dict_raw(db) or {}
    ev = event_from_bundle(bundle, session.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    station_uuid = (body.station_uuid or "").strip()
    if not station_uuid:
        for st in (ev.get("configuration") or {}).get("stations") or []:
            su = str(st.get("uuid") or "").strip()
            if su:
                station_uuid = su
                break
    if not station_uuid:
        raise HTTPException(status_code=422, detail="station_uuid required")
    if session.status == "OPEN":
        close_session(db, session, counted_cash_cents=body.counted_cash_cents)
        sync_cash_session(db, session)
    esc = _shift_receipt_escpos(
        db, session, ev, paper_width=body.paper_width, charset=body.charset
    )
    host, port, feed_lines = resolve_printer_endpoint(ev, station_uuid)
    job = PrintJob(
        local_order_id=0,
        station_uuid=station_uuid,
        job_kind="shift_close",
        printer_host=host,
        printer_port=port,
        escpos_payload=base64.b64encode(esc).decode("ascii"),
        status="queued",
    )
    db.add(job)
    db.flush()
    try:
        asyncio.run(_send_to_printer(host, port, esc))
        job.status = "sent"
    except Exception as exc:
        job.status = "error"
        job.last_error = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.commit()
    return ShiftSessionPrintResponse(ok=True, print_job_id=job.id)
