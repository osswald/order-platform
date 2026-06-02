"""Test helpers for v3 order submissions."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import LocalOrder
from app.models_operational import OrderSession


def seed_open_submission(
    db: Session,
    *,
    client_order_id: str,
    event_id: int,
    table_number: int,
    payload: dict,
) -> LocalOrder:
    session = OrderSession(
        event_id=event_id,
        table_number=table_number,
        order_source="waiter",
        status="OPEN",
    )
    db.add(session)
    db.flush()
    order = LocalOrder(
        session_id=int(session.id),
        client_order_id=client_order_id,
        event_id=event_id,
        table_number=table_number,
        payment_status="open",
        payload_json=json.dumps(payload),
    )
    db.add(order)
    db.flush()
    return order
