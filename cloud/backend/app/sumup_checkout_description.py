"""Compose SumUp Merchant Sales checkout descriptions."""

from __future__ import annotations

DESCRIPTION_MAX_LEN = 90
_SEPARATOR = " · "
_ELLIPSIS = "…"


def sumup_checkout_description(
    event_name: str | None,
    solo_label: str | None,
    waiter_name: str | None = None,
) -> str | None:
    """Join event, Solo label, and waiter; skip blanks; cap at 90 characters."""
    parts: list[str] = []
    for raw in (event_name, solo_label, waiter_name):
        text = (raw or "").strip()
        if text:
            parts.append(text)
    if not parts:
        return None
    joined = _SEPARATOR.join(parts)
    if len(joined) <= DESCRIPTION_MAX_LEN:
        return joined
    if DESCRIPTION_MAX_LEN <= 1:
        return _ELLIPSIS[:DESCRIPTION_MAX_LEN]
    return joined[: DESCRIPTION_MAX_LEN - 1] + _ELLIPSIS
