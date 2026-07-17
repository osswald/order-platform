"""Organisation-scoped currency helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Event, Organisation


def organisation_currency(org: Organisation | None, fallback: str = "EUR") -> str:
    raw = getattr(org, "currency", None) if org else None
    return (raw or fallback).upper()


def organisation_country_code(org: Organisation | None, fallback: str = "CH") -> str:
    country = getattr(org, "country", None) if org else None
    code = getattr(country, "code", None) if country else None
    return (code or fallback).upper()


def event_country_code(event: Event | None, fallback: str = "CH") -> str:
    if event is None:
        return fallback.upper()
    org = getattr(event, "organisation", None)
    return organisation_country_code(org, fallback)


def event_currency(event: Event | None, fallback: str = "EUR") -> str:
    if event is None:
        return fallback.upper()
    org = getattr(event, "organisation", None)
    return organisation_currency(org, fallback)
