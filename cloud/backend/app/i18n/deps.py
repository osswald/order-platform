"""FastAPI dependencies for locale resolution."""

from __future__ import annotations

from fastapi import Header

from . import DEFAULT_LOCALE, resolve_locale_from_accept_language


def get_locale(accept_language: str | None = Header(default=None)) -> str:
    return resolve_locale_from_accept_language(accept_language) or DEFAULT_LOCALE
