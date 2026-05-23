"""Event lifecycle status: config → test → prod → archive."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import EdgeSubmittedOrder, Event, EventCollectiveBill
from .stock import reset_event_stock_to_baseline

ALLOWED_STATUSES = frozenset({"config", "test", "prod", "archive"})
PI_VISIBLE_STATUSES = frozenset({"test", "prod"})
ORDER_ACCEPT_STATUSES = frozenset({"test", "prod"})

STATUS_LABELS = {
    "config": "Konfiguration",
    "test": "Testbetrieb",
    "prod": "Produktivbetrieb",
    "archive": "Archiviert",
}

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "config": frozenset({"test"}),
    "test": frozenset({"prod"}),
    "prod": frozenset({"archive"}),
    "archive": frozenset(),
}


def normalize_status(value: str | None) -> str:
    return (value or "config").lower()


def next_statuses(current: str) -> frozenset[str]:
    return ALLOWED_TRANSITIONS.get(normalize_status(current), frozenset())


def selectable_statuses(current: str) -> list[str]:
    cur = normalize_status(current)
    nxt = next_statuses(cur)
    if cur in nxt:
        return [cur]
    return [cur, *sorted(nxt)]


def assert_create_status(value: str) -> str:
    st = normalize_status(value)
    if st != "config":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New events must have status config",
        )
    return st


def validate_status_transition(old: str, new: str) -> None:
    old_n = normalize_status(old)
    new_n = normalize_status(new)
    if old_n == new_n:
        return
    if new_n not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}",
        )
    allowed = ALLOWED_TRANSITIONS.get(old_n, frozenset())
    if new_n not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot transition from {old_n} to {new_n}",
        )


def purge_event_operational_data(db: Session, event: Event) -> None:
    """Remove test orders/stats and reset stock when entering production."""
    db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event.id).delete(
        synchronize_session=False
    )
    db.query(EventCollectiveBill).filter(EventCollectiveBill.event_id == event.id).delete(
        synchronize_session=False
    )
    reset_event_stock_to_baseline(db, event)
