"""Locale-aware formatting helpers for PDF documents."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

_INTL_LOCALES = {"de": "de-CH", "en": "en-CH"}


def intl_locale(locale: str) -> str:
    return _INTL_LOCALES.get(locale, _INTL_LOCALES["de"])


def format_amount(cents: int | None, locale: str = "de") -> str:
    value = (cents or 0) / 100.0
    formatted = f"{value:,.2f}".replace(",", "'")
    if locale == "en":
        formatted = f"{value:,.2f}"
    return formatted


def format_money(cents: int | None, *, locale: str = "de", currency: str = "CHF") -> str:
    return f"{format_amount(cents, locale)} {currency}"


def _parse_iso(iso: str | None) -> datetime | None:
    if not iso:
        return None
    text = str(iso).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def format_datetime(iso: str | datetime | None, locale: str = "de") -> str:
    if isinstance(iso, datetime):
        dt = iso
    else:
        dt = _parse_iso(iso)
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    if locale == "en":
        return dt.astimezone(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y %H:%M")
    return dt.astimezone(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y %H:%M")


def format_event_range(start_iso: str | datetime | None, end_iso: str | datetime | None, locale: str = "de") -> str:
    start = format_datetime(start_iso, locale)
    end = format_datetime(end_iso, locale)
    if start == "—" and end == "—":
        return "—"
    return f"{start} – {end}"


def safe_filename(name: str, *, fallback: str = "document") -> str:
    cleaned = re.sub(r"[^\w\s\-]+", "", name or "", flags=re.UNICODE)
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    return cleaned[:80] or fallback


def organisation_issuer_lines(organisation) -> list[str]:
    lines: list[str] = []
    if organisation is None:
        return lines
    if getattr(organisation, "name", None):
        lines.append(str(organisation.name))
    address = getattr(organisation, "address", None)
    if address:
        lines.append(str(address))
    zip_code = getattr(organisation, "zip", None) or ""
    city = getattr(organisation, "city", None) or ""
    city_line = " ".join(part for part in (str(zip_code).strip(), str(city).strip()) if part)
    if city_line:
        lines.append(city_line)
    return lines
