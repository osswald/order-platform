"""Event lifecycle status: config → test → prod → archive."""

from __future__ import annotations

from fastapi import status
from .i18n.errors import api_error
from sqlalchemy.orm import Session

from .models import EdgeSubmittedOrder, Event, EventCollectiveBill
from .stock import reset_event_stock_to_baseline

ALLOWED_STATUSES = frozenset({"config", "test", "prod", "archive"})
PI_VISIBLE_STATUSES = frozenset({"test", "prod"})
ORDER_ACCEPT_STATUSES = frozenset({"test", "prod"})

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
        raise api_error("new_event_must_config", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return st


def validate_status_transition(old: str, new: str) -> None:
    old_n = normalize_status(old)
    new_n = normalize_status(new)
    if old_n == new_n:
        return
    if new_n not in ALLOWED_STATUSES:
        raise api_error("status_must_be_one_of", status.HTTP_422_UNPROCESSABLE_ENTITY, statuses=", ".join(sorted(ALLOWED_STATUSES)))
    allowed = ALLOWED_TRANSITIONS.get(old_n, frozenset())
    if new_n not in allowed:
        raise api_error("cannot_transition_status", status.HTTP_422_UNPROCESSABLE_ENTITY, old_status=old_n, new_status=new_n)


def purge_event_operational_data(db: Session, event: Event) -> None:
    """Remove test orders/stats and reset stock when entering production."""
    db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == event.id).delete(
        synchronize_session=False
    )
    db.query(EventCollectiveBill).filter(EventCollectiveBill.event_id == event.id).delete(
        synchronize_session=False
    )
    reset_event_stock_to_baseline(db, event)
