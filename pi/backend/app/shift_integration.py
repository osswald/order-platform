"""Wire cash shift sessions into orders and payments."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .domain.cash_sessions import (
    record_order_on_session,
    record_payments_on_session,
    record_voucher_redemption_on_session,
    resolve_session_for_context,
    session_to_sync_payload,
    shift_settlement_enabled,
)
from .domain.sync_enqueue import enqueue_cash_session_sync
from .vouchers import voucher_definition_by_uuid


def sync_cash_session(db: Session, session) -> None:
    payload = session_to_sync_payload(db, session)
    enqueue_cash_session_sync(db, event_id=int(session.event_id), payload=payload)


def session_to_api_dict(session) -> dict[str, Any]:
    return {
        "id": int(session.id),
        "event_id": int(session.event_id),
        "subject_type": session.subject_type,
        "subject_name": session.subject_name or "",
        "status": session.status,
        "opening_balance_cents": int(session.opening_balance_cents or 0),
        "wallet_cents": int(session.wallet_cents or 0),
        "total_cash_cents": int(session.total_cash_cents or 0),
        "total_non_cash_cents": int(session.total_non_cash_cents or 0),
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }


def attach_shift_to_payload(
    db: Session,
    ev: dict,
    payload: dict,
    *,
    event_id: int,
    waiter_uuid: str | None,
    cash_register_uuid: str | None,
) -> Any | None:
    session = resolve_session_for_context(
        db,
        ev,
        event_id=event_id,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    if session:
        payload["cash_session_id"] = int(session.id)
    return session


def record_shift_order_submit(
    db: Session,
    ev: dict,
    *,
    event_id: int,
    waiter_uuid: str | None,
    cash_register_uuid: str | None,
    amount_cents: int,
    reference_id: str | None,
    voucher_records: list[dict] | None = None,
) -> None:
    if not shift_settlement_enabled(ev):
        return
    session = resolve_session_for_context(
        db,
        ev,
        event_id=event_id,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    if not session:
        return
    if amount_cents > 0:
        record_order_on_session(db, session, amount_cents=amount_cents, reference_id=reference_id)
    if voucher_records:
        for rec in voucher_records:
            if not isinstance(rec, dict):
                continue
            v_uuid = str(rec.get("voucher_definition_uuid") or "").strip()
            vd = voucher_definition_by_uuid(ev, v_uuid) if v_uuid else None
            name = str((vd or {}).get("name") or rec.get("name") or "Gutschein")
            amount = int(rec.get("applied_cents") or rec.get("credit_cents") or rec.get("amount_cents") or 0)
            if amount <= 0:
                continue
            record_voucher_redemption_on_session(
                db,
                session,
                amount_cents=amount,
                voucher_definition_uuid=v_uuid or None,
                voucher_name=name,
                reference_id=reference_id,
            )
    sync_cash_session(db, session)


def record_shift_payments(
    db: Session,
    ev: dict,
    payload: dict,
    *,
    event_id: int,
    reference_id: str | None,
) -> None:
    if not shift_settlement_enabled(ev):
        return
    waiter_uuid = payload.get("waiter_uuid")
    cash_register_uuid = payload.get("cash_register_uuid")
    payments = payload.get("payments") or []
    voucher_records = payload.get("voucher_redemptions") or []
    session = resolve_session_for_context(
        db,
        ev,
        event_id=event_id,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    if not session:
        return
    payload["cash_session_id"] = int(session.id)
    if payments:
        record_payments_on_session(db, session, payments, reference_id=reference_id)
    if voucher_records:
        for rec in voucher_records:
            if not isinstance(rec, dict):
                continue
            v_uuid = str(rec.get("voucher_definition_uuid") or "").strip()
            vd = voucher_definition_by_uuid(ev, v_uuid) if v_uuid else None
            name = str((vd or {}).get("name") or rec.get("name") or "Gutschein")
            amount = int(rec.get("applied_cents") or rec.get("credit_cents") or rec.get("amount_cents") or 0)
            if amount <= 0:
                continue
            record_voucher_redemption_on_session(
                db,
                session,
                amount_cents=amount,
                voucher_definition_uuid=v_uuid or None,
                voucher_name=name,
                reference_id=reference_id,
            )
    sync_cash_session(db, session)


def record_shift_for_order(
    db: Session,
    ev: dict,
    *,
    event_id: int,
    waiter_uuid: str | None,
    cash_register_uuid: str | None,
    amount_cents: int,
    reference_id: str | None,
    payments: list[dict] | None = None,
    voucher_records: list[dict] | None = None,
) -> None:
    if not shift_settlement_enabled(ev):
        return
    session = resolve_session_for_context(
        db,
        ev,
        event_id=event_id,
        waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
    )
    if not session:
        return
    if amount_cents > 0:
        record_order_on_session(db, session, amount_cents=amount_cents, reference_id=reference_id)
    if payments:
        record_payments_on_session(db, session, payments, reference_id=reference_id)
    if voucher_records:
        for rec in voucher_records:
            if not isinstance(rec, dict):
                continue
            v_uuid = str(rec.get("voucher_definition_uuid") or "").strip()
            vd = voucher_definition_by_uuid(ev, v_uuid) if v_uuid else None
            name = str((vd or {}).get("name") or rec.get("name") or "Gutschein")
            amount = int(rec.get("applied_cents") or rec.get("credit_cents") or rec.get("amount_cents") or 0)
            if amount <= 0:
                continue
            record_voucher_redemption_on_session(
                db,
                session,
                amount_cents=amount,
                voucher_definition_uuid=v_uuid or None,
                voucher_name=name,
                reference_id=reference_id,
            )
    sync_cash_session(db, session)


def record_shift_for_payment_receipt(
    db: Session,
    ev: dict,
    payload: dict,
    *,
    event_id: int,
    reference_id: str | None,
) -> None:
    record_shift_payments(db, ev, payload, event_id=event_id, reference_id=reference_id)
