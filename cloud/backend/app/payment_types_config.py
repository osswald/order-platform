"""Payment type allowlist and normalization (backed by payment_types table)."""

from __future__ import annotations

from sqlalchemy.orm import Session

FALLBACK_PAYMENT_TYPES = frozenset({"cash", "twint", "sumup", "stripe_terminal"})
FALLBACK_PAYMENT_TYPE_ORDER = ("cash", "twint", "sumup", "stripe_terminal")

_allowed_slugs: frozenset[str] = FALLBACK_PAYMENT_TYPES
_slug_order: tuple[str, ...] = FALLBACK_PAYMENT_TYPE_ORDER


def refresh_payment_types_cache(db: Session) -> None:
    global _allowed_slugs, _slug_order
    from .models import PaymentType

    rows = (
        db.query(PaymentType)
        .filter(PaymentType.is_active.is_(True))
        .order_by(PaymentType.sort_order, PaymentType.slug)
        .all()
    )
    if not rows:
        _allowed_slugs = FALLBACK_PAYMENT_TYPES
        _slug_order = FALLBACK_PAYMENT_TYPE_ORDER
        return
    slugs = tuple(row.slug for row in rows)
    _allowed_slugs = frozenset(slugs)
    _slug_order = slugs


def allowed_payment_type_slugs() -> frozenset[str]:
    return _allowed_slugs


def payment_type_order() -> tuple[str, ...]:
    return _slug_order


def normalize_payment_types(types: list[str] | None) -> list[str]:
    if not types:
        return ["cash"] if "cash" in _allowed_slugs else [next(iter(_slug_order), "cash")]
    out: list[str] = []
    seen: set[str] = set()
    for raw in types:
        key = (raw or "").strip().lower()
        if key not in _allowed_slugs or key in seen:
            continue
        seen.add(key)
        out.append(key)
    if not out:
        allowed = ", ".join(sorted(_allowed_slugs))
        raise ValueError(f"payment_types must contain at least one of: {allowed}")
    order_index = {slug: index for index, slug in enumerate(_slug_order)}
    return sorted(out, key=lambda x: order_index.get(x, len(_slug_order)))


def payment_types_from_event(event) -> list[str]:
    raw = getattr(event, "payment_types", None)
    if isinstance(raw, list) and raw:
        try:
            return normalize_payment_types(raw)
        except ValueError:
            return ["cash"] if "cash" in _allowed_slugs else [next(iter(_slug_order), "cash")]
    return ["cash"] if "cash" in _allowed_slugs else [next(iter(_slug_order), "cash")]
