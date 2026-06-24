"""Kellner-/Kassenabrechnung — cash shift sessions and ledger."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models_operational import CashSession, CashSessionLedger
from ..order_fiscal import waiter_name_from_event


def shift_settlement_enabled(ev: dict) -> bool:
    return bool(ev.get("shift_settlement_enabled"))


def _subject_name(ev: dict, *, subject_type: str, waiter_uuid: str | None, cash_register_uuid: str | None) -> str:
    if subject_type == "waiter" and waiter_uuid:
        return waiter_name_from_event(ev, waiter_uuid) or str(waiter_uuid)
    if subject_type == "cash_register" and cash_register_uuid:
        for reg in (ev.get("configuration") or {}).get("cash_registers") or []:
            if str(reg.get("uuid")) == str(cash_register_uuid):
                return str(reg.get("name") or cash_register_uuid)
        return str(cash_register_uuid)
    return "—"


def _open_query(db: Session, *, event_id: int, subject_type: str, waiter_uuid: str | None, cash_register_uuid: str | None):
    q = db.query(CashSession).filter(
        CashSession.event_id == event_id,
        CashSession.subject_type == subject_type,
        CashSession.status == "OPEN",
    )
    if subject_type == "waiter":
        return q.filter(CashSession.waiter_uuid == waiter_uuid)
    return q.filter(CashSession.cash_register_uuid == cash_register_uuid)


def get_open_session(
    db: Session,
    *,
    event_id: int,
    subject_type: str,
    waiter_uuid: str | None = None,
    cash_register_uuid: str | None = None,
) -> CashSession | None:
    return _open_query(
        db,
        event_id=event_id,
        subject_type=subject_type,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    ).order_by(CashSession.id.desc()).first()


def open_session(
    db: Session,
    ev: dict,
    *,
    event_id: int,
    subject_type: str,
    opening_balance_cents: int,
    waiter_uuid: str | None = None,
    cash_register_uuid: str | None = None,
    operator_waiter_uuid: str | None = None,
) -> CashSession:
    subject_type = (subject_type or "").strip().lower()
    if subject_type not in ("waiter", "cash_register"):
        raise HTTPException(status_code=400, detail="Invalid subject_type")
    if subject_type == "waiter" and not waiter_uuid:
        raise HTTPException(status_code=400, detail="waiter_uuid required")
    if subject_type == "cash_register" and not cash_register_uuid:
        raise HTTPException(status_code=400, detail="cash_register_uuid required")

    existing = get_open_session(
        db,
        event_id=event_id,
        subject_type=subject_type,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Shift already open")

    opening = max(0, int(opening_balance_cents or 0))
    name = _subject_name(
        ev,
        subject_type=subject_type,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    session = CashSession(
        event_id=event_id,
        subject_type=subject_type,
        waiter_uuid=waiter_uuid if subject_type == "waiter" else None,
        cash_register_uuid=cash_register_uuid if subject_type == "cash_register" else None,
        subject_name=name,
        operator_waiter_uuid=operator_waiter_uuid,
        status="OPEN",
        opening_balance_cents=opening,
        wallet_cents=opening,
        total_cash_cents=0,
        total_non_cash_cents=0,
        total_card_cents=0,
    )
    db.add(session)
    db.flush()
    return session


def _is_cash_method(method: str) -> bool:
    return str(method or "").strip().lower() == "cash"


def append_ledger(
    db: Session,
    session: CashSession,
    *,
    entry_type: str,
    amount_cents: int,
    affects_wallet: bool,
    method: str | None = None,
    voucher_definition_uuid: str | None = None,
    voucher_name: str | None = None,
    reference_id: str | None = None,
    payload: dict | None = None,
) -> CashSessionLedger:
    row = CashSessionLedger(
        cash_session_id=int(session.id),
        entry_type=entry_type,
        amount_cents=max(0, int(amount_cents or 0)),
        affects_wallet=1 if affects_wallet else 0,
        method=method,
        voucher_definition_uuid=voucher_definition_uuid,
        voucher_name=voucher_name,
        reference_id=str(reference_id) if reference_id is not None else None,
        payload_json=json.dumps(payload or {}),
    )
    db.add(row)
    db.flush()
    return row


def record_order_on_session(db: Session, session: CashSession, *, amount_cents: int, reference_id: str | None) -> None:
    append_ledger(
        db,
        session,
        entry_type="order",
        amount_cents=amount_cents,
        affects_wallet=False,
        reference_id=reference_id,
    )


def record_payments_on_session(
    db: Session,
    session: CashSession,
    payments: list[dict],
    *,
    reference_id: str | None = None,
) -> None:
    for p in payments or []:
        if not isinstance(p, dict):
            continue
        amount = int(p.get("amount_cents") or 0)
        method = str(p.get("type") or "cash").lower()
        is_cash = _is_cash_method(method)
        append_ledger(
            db,
            session,
            entry_type="payment",
            amount_cents=amount,
            affects_wallet=is_cash,
            method=method,
            reference_id=reference_id,
            payload=p,
        )
        if is_cash:
            session.total_cash_cents = int(session.total_cash_cents or 0) + amount
            session.wallet_cents = int(session.wallet_cents or 0) + amount
        else:
            session.total_non_cash_cents = int(session.total_non_cash_cents or 0) + amount
            session.total_card_cents = int(session.total_non_cash_cents or 0)


def record_voucher_redemption_on_session(
    db: Session,
    session: CashSession,
    *,
    amount_cents: int,
    voucher_definition_uuid: str | None,
    voucher_name: str | None,
    reference_id: str | None = None,
) -> None:
    append_ledger(
        db,
        session,
        entry_type="voucher_redemption",
        amount_cents=amount_cents,
        affects_wallet=False,
        voucher_definition_uuid=voucher_definition_uuid,
        voucher_name=voucher_name,
        reference_id=reference_id,
    )


def ledger_aggregates(db: Session, session_id: int) -> tuple[dict[str, int], dict[str, int]]:
    rows = db.query(CashSessionLedger).filter(CashSessionLedger.cash_session_id == session_id).all()
    by_method: dict[str, int] = defaultdict(int)
    by_voucher: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.entry_type == "payment" and row.method:
            by_method[str(row.method)] += int(row.amount_cents or 0)
        if row.entry_type == "voucher_redemption":
            label = (row.voucher_name or row.voucher_definition_uuid or "Gutschein").strip()
            by_voucher[label] += int(row.amount_cents or 0)
    return dict(by_method), dict(by_voucher)


def close_session(
    db: Session,
    session: CashSession,
    *,
    counted_cash_cents: int,
) -> CashSession:
    if session.status != "OPEN":
        raise HTTPException(status_code=400, detail="Shift not open")
    counted = max(0, int(counted_cash_cents or 0))
    expected = int(session.wallet_cents or 0)
    session.counted_cash_cents = counted
    session.variance_cents = counted - expected
    session.status = "CLOSED"
    session.ended_at = datetime.now(timezone.utc)
    db.flush()
    return session


def session_to_sync_payload(db: Session, session: CashSession) -> dict[str, Any]:
    by_method, by_voucher = ledger_aggregates(db, int(session.id))
    ledger_rows = db.query(CashSessionLedger).filter(CashSessionLedger.cash_session_id == session.id).all()
    subject_type = str(session.subject_type or "waiter").lower()
    if subject_type == "cash_register" and session.cash_register_uuid:
        subject_key = f"cash_register:{session.cash_register_uuid}"
    elif session.waiter_uuid:
        subject_key = f"waiter:{session.waiter_uuid}"
    else:
        subject_key = None
    return {
        "cash_session_id": int(session.id),
        "subject_key": subject_key,
        "event_id": int(session.event_id),
        "subject_type": session.subject_type,
        "waiter_uuid": session.waiter_uuid,
        "cash_register_uuid": session.cash_register_uuid,
        "subject_name": session.subject_name,
        "operator_waiter_uuid": session.operator_waiter_uuid,
        "status": session.status,
        "opening_balance_cents": int(session.opening_balance_cents or 0),
        "wallet_cents": int(session.wallet_cents or 0),
        "total_cash_cents": int(session.total_cash_cents or 0),
        "total_non_cash_cents": int(session.total_non_cash_cents or 0),
        "counted_cash_cents": session.counted_cash_cents,
        "variance_cents": session.variance_cents,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "payments_by_method": by_method,
        "vouchers_by_definition": by_voucher,
        "ledger": [
            {
                "entry_type": r.entry_type,
                "amount_cents": r.amount_cents,
                "affects_wallet": bool(r.affects_wallet),
                "method": r.method,
                "voucher_name": r.voucher_name,
                "reference_id": r.reference_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in ledger_rows
        ],
    }


def resolve_session_for_context(
    db: Session,
    ev: dict,
    *,
    event_id: int,
    waiter_uuid: str | None,
    cash_register_uuid: str | None,
) -> CashSession | None:
    if not shift_settlement_enabled(ev):
        return None
    if cash_register_uuid:
        return get_open_session(
            db,
            event_id=event_id,
            subject_type="cash_register",
            cash_register_uuid=cash_register_uuid,
        )
    if waiter_uuid:
        return get_open_session(
            db,
            event_id=event_id,
            subject_type="waiter",
            waiter_uuid=waiter_uuid,
        )
    return None
