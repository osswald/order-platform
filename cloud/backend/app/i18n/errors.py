"""Structured API errors with localized messages."""

from __future__ import annotations

from fastapi import HTTPException

from . import t
from .context import get_request_locale


def api_error(
    code: str,
    status_code: int,
    locale: str | None = None,
    **params: object,
) -> HTTPException:
    loc = locale or get_request_locale()
    message = t(f"errors.{code}", loc, **params)
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def detail_message(detail: object) -> str:
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str):
            return message
    if isinstance(detail, str):
        return detail
    return str(detail)
