"""Cloud reporting for Pi cash shift sessions."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .currency import event_country_code, event_currency
from .edge_operational_keys import cash_session_subject_key
from .models import EdgeCashSession, Event


def build_cash_sessions_page(
    db: Session,
    event: Event,
    *,
    page: int = 1,
    items_per_page: int = 25,
    sort_by: str | None = "started_at",
    sort_desc: bool = True,
) -> dict[str, Any]:
    q = db.query(EdgeCashSession).filter(EdgeCashSession.event_id == event.id)
    total = q.count()
    sort_key = (sort_by or "started_at").strip()

    def row_key(row: EdgeCashSession):
        if sort_key == "subject_name":
            return (row.subject_name or "").lower()
        if sort_key == "status":
            return row.status or ""
        if sort_key == "ended_at":
            return row.ended_at or row.started_at
        return row.started_at

    rows = q.all()
    rows.sort(key=row_key, reverse=sort_desc)
    start = max(0, (page - 1) * items_per_page)
    page_rows = rows[start : start + items_per_page]

    waiter_names = {w.uuid: w.name for w in event.event_waiters or []}

    items = []
    for row in page_rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        items.append(
            {
                "id": row.id,
                "cash_session_id": row.cash_session_id,
                "subject_type": row.subject_type,
                "subject_name": row.subject_name,
                "operator_waiter_name": waiter_names.get(row.operator_waiter_uuid or "", "—")
                if row.operator_waiter_uuid
                else "—",
                "status": row.status,
                "opening_balance_cents": row.opening_balance_cents,
                "wallet_cents": row.wallet_cents,
                "total_cash_cents": row.total_cash_cents,
                "total_non_cash_cents": row.total_non_cash_cents,
                "counted_cash_cents": row.counted_cash_cents,
                "variance_cents": row.variance_cents,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                "ledger": payload.get("ledger") or [],
                "payments_by_method": payload.get("payments_by_method") or {},
                "vouchers_by_definition": payload.get("vouchers_by_definition") or {},
            }
        )

    return {
        "currency": event_currency(event, "EUR"),
        "country_code": event_country_code(event, "CH"),
        "total": total,
        "page": page,
        "items_per_page": items_per_page,
        "items": items,
    }


def upsert_edge_cash_session(
    db: Session,
    *,
    organisation_id: int,
    appliance_id: int,
    event_id: int,
    payload: dict,
) -> None:
    from datetime import datetime

    cash_session_id = int(payload.get("cash_session_id") or 0)
    subject_key = cash_session_subject_key(payload) or payload.get("subject_key")
    if not cash_session_id or not subject_key:
        return

    def _parse_dt(val):
        if not val:
            return None
        if isinstance(val, datetime):
            return val
        try:
            return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        except ValueError:
            return None

    existing = (
        db.query(EdgeCashSession)
        .filter(
            EdgeCashSession.organisation_id == organisation_id,
            EdgeCashSession.event_id == event_id,
            EdgeCashSession.subject_key == subject_key,
        )
        .first()
    )
    fields = {
        "organisation_id": organisation_id,
        "appliance_id": appliance_id,
        "event_id": event_id,
        "subject_key": subject_key,
        "cash_session_id": cash_session_id,
        "subject_type": str(payload.get("subject_type") or "waiter"),
        "waiter_uuid": payload.get("waiter_uuid"),
        "cash_register_uuid": payload.get("cash_register_uuid"),
        "subject_name": str(payload.get("subject_name") or ""),
        "operator_waiter_uuid": payload.get("operator_waiter_uuid"),
        "status": str(payload.get("status") or "OPEN"),
        "opening_balance_cents": int(payload.get("opening_balance_cents") or 0),
        "wallet_cents": int(payload.get("wallet_cents") or 0),
        "total_cash_cents": int(payload.get("total_cash_cents") or 0),
        "total_non_cash_cents": int(payload.get("total_non_cash_cents") or 0),
        "counted_cash_cents": payload.get("counted_cash_cents"),
        "variance_cents": payload.get("variance_cents"),
        "payload": payload,
        "started_at": _parse_dt(payload.get("started_at")),
        "ended_at": _parse_dt(payload.get("ended_at")),
    }
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(EdgeCashSession(**fields))
