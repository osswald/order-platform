"""Organisation-scoped first-event setup wizard state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session, joinedload

from .i18n.errors import api_error
from .models import Event, EventStation, Organisation


def _utc_now() -> datetime:
    return datetime.now(UTC)


def first_event_setup_state(organisation: Organisation) -> dict[str, Any]:
    completed = organisation.first_event_setup_completed_at is not None
    dismissed = organisation.first_event_setup_dismissed_at is not None
    return {
        "available": not completed and not dismissed,
        "completed": completed,
        "dismissed": dismissed,
        "in_progress_event_id": organisation.first_event_setup_event_id,
    }


def event_is_minimally_configured(event: Event) -> bool:
    has_station_articles = any(len(station.articles or []) > 0 for station in (event.stations or []))
    has_event_waiter = len(event.event_waiters or []) > 0
    has_layout = len(event.app_layouts or []) > 0
    return has_station_articles and has_event_waiter and has_layout


def organisation_has_minimally_configured_event(db: Session, organisation_id: int) -> bool:
    events = (
        db.query(Event)
        .options(
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts),
        )
        .filter(Event.organisation_id == organisation_id)
        .all()
    )
    return any(event_is_minimally_configured(event) for event in events)


def maybe_auto_complete_first_event_setup(db: Session, organisation: Organisation) -> bool:
    """Mark setup complete when a mature org already has a minimal event config.

    Returns True when the organisation was updated.
    """
    if organisation.first_event_setup_completed_at is not None:
        return False
    if organisation.first_event_setup_dismissed_at is not None:
        return False
    if not organisation_has_minimally_configured_event(db, organisation.id):
        return False
    organisation.first_event_setup_completed_at = _utc_now()
    organisation.first_event_setup_event_id = None
    return True


def dismiss_first_event_setup(organisation: Organisation) -> None:
    if organisation.first_event_setup_dismissed_at is None:
        organisation.first_event_setup_dismissed_at = _utc_now()


def complete_first_event_setup(organisation: Organisation) -> None:
    if organisation.first_event_setup_completed_at is None:
        organisation.first_event_setup_completed_at = _utc_now()
    organisation.first_event_setup_event_id = None


def set_first_event_setup_in_progress_event(
    db: Session,
    organisation: Organisation,
    event_id: int | None,
) -> None:
    if event_id is None:
        organisation.first_event_setup_event_id = None
        return
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.organisation_id == organisation.id)
        .first()
    )
    if event is None:
        raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT)
    organisation.first_event_setup_event_id = event_id
