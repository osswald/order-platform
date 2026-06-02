"""Order session helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models_operational import OrderSession


def ensure_order_session(
    db: Session,
    *,
    event_id: int,
    table_number: int | None,
    waiter_uuid: str | None,
    order_source: str,
    cash_register_uuid: str | None = None,
    pickup_code: str | None = None,
) -> int:
    """Return session id for table/register flow (reuse OPEN session when possible)."""
    q = db.query(OrderSession).filter(
        OrderSession.event_id == event_id,
        OrderSession.status == "OPEN",
    )
    if order_source == "cash_register" and cash_register_uuid:
        row = q.filter(OrderSession.cash_register_uuid == cash_register_uuid).order_by(OrderSession.id.desc()).first()
    elif table_number and table_number > 0:
        row = q.filter(OrderSession.table_number == table_number).order_by(OrderSession.id.desc()).first()
    else:
        row = None
    if row:
        return int(row.id)
    session = OrderSession(
        event_id=event_id,
        table_number=table_number if table_number and table_number > 0 else None,
        pickup_code=pickup_code,
        opened_by_waiter_uuid=waiter_uuid,
        cash_register_uuid=cash_register_uuid,
        order_source=order_source,
        status="OPEN",
    )
    db.add(session)
    db.flush()
    return int(session.id)
