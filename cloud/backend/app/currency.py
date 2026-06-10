"""Organisation-scoped currency helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Event, Organisation


def organisation_currency(org: Organisation | None, fallback: str = "EUR") -> str:
    raw = getattr(org, "currency", None) if org else None
    return (raw or fallback).upper()


def event_currency(event: Event | None, fallback: str = "EUR") -> str:
    if event is None:
        return fallback.upper()
    org = getattr(event, "organisation", None)
    return organisation_currency(org, fallback)
