"""Allowed Pi payment types per event."""

from __future__ import annotations

ALLOWED_PAYMENT_TYPES = frozenset({"cash", "twint", "sumup", "stripe_terminal"})
PAYMENT_TYPE_ORDER = ("cash", "twint", "sumup", "stripe_terminal")


def normalize_payment_types(types: list[str] | None) -> list[str]:
    if not types:
        return ["cash"]
    out: list[str] = []
    seen: set[str] = set()
    for raw in types:
        key = (raw or "").strip().lower()
        if key not in ALLOWED_PAYMENT_TYPES or key in seen:
            continue
        seen.add(key)
        out.append(key)
    if not out:
        raise ValueError(
            f"payment_types must contain at least one of: {', '.join(sorted(ALLOWED_PAYMENT_TYPES))}"
        )
    return sorted(out, key=lambda x: PAYMENT_TYPE_ORDER.index(x))


def payment_types_from_event(event) -> list[str]:
    raw = getattr(event, "payment_types", None)
    if isinstance(raw, list) and raw:
        try:
            return normalize_payment_types(raw)
        except ValueError:
            return ["cash"]
    return ["cash"]
