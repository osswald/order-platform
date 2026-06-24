"""Validation and persistence for instant-mode event Sammelrechnung settings."""

from __future__ import annotations

import uuid as uuid_lib

from fastapi import status

from .i18n.errors import api_error
from .models import Event


def _normalize_name(name: str | None) -> str:
    return str(name or "").strip()


def apply_instant_collective_bill_settings(
    event: Event,
    *,
    payment_mode: str | None = None,
    instant_collective_bill_name: str | None = None,
    payment_mode_set: bool = False,
    instant_collective_bill_name_set: bool = False,
) -> None:
    pm = (payment_mode if payment_mode_set else getattr(event, "payment_mode", None) or "pay_later").lower()
    name = (
        _normalize_name(instant_collective_bill_name)
        if instant_collective_bill_name_set
        else _normalize_name(getattr(event, "instant_collective_bill_name", None))
    )

    if pm == "instant":
        if not name:
            raise api_error("instant_collective_bill_name_required", status.HTTP_422_UNPROCESSABLE_CONTENT)
        event.instant_collective_bill_name = name
        if not getattr(event, "instant_collective_bill_uuid", None):
            event.instant_collective_bill_uuid = str(uuid_lib.uuid4())
        return

    if payment_mode_set and pm != "instant":
        event.instant_collective_bill_name = None
        event.instant_collective_bill_uuid = None
    elif instant_collective_bill_name_set:
        event.instant_collective_bill_name = name or None


def instant_collective_bill_fields(event: Event) -> dict[str, str | None]:
    return {
        "instant_collective_bill_name": getattr(event, "instant_collective_bill_name", None),
        "instant_collective_bill_uuid": getattr(event, "instant_collective_bill_uuid", None),
    }
