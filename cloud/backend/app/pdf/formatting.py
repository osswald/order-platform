"""Locale-aware formatting helpers for PDF documents."""

from __future__ import annotations

import re

from ..locale_format import (
    format_amount,
    format_datetime,
    format_event_range,
    format_money,
    intl_locale,
    resolve_format_locale,
)

__all__ = [
    "format_amount",
    "format_datetime",
    "format_event_range",
    "format_money",
    "intl_locale",
    "organisation_issuer_lines",
    "resolve_format_locale",
    "safe_filename",
]


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
