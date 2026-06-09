"""Request-scoped locale via context variable."""

from __future__ import annotations

from contextvars import ContextVar

from . import DEFAULT_LOCALE

_locale_ctx: ContextVar[str] = ContextVar("locale", default=DEFAULT_LOCALE)


def get_request_locale() -> str:
    return _locale_ctx.get()


def set_request_locale(locale: str) -> None:
    _locale_ctx.set(locale)
