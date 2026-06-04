"""Order and line discount validation and helpers."""

from __future__ import annotations

from fastapi import HTTPException

from .pricing import (
    apply_discount_cents,
    discounts_enabled,
    line_gross_cents,
    normalize_discount,
)
from .vouchers import is_voucher_sale_line, voucher_sale_unit_cents


def validate_submit_discounts(
    ev: dict,
    lines: list,
    order_discount: dict | None,
    articles: dict,
) -> dict | None:
    """Reject discount fields when disabled; normalize and cap discounts when enabled."""
    enabled = discounts_enabled(ev)
    normalized_order = normalize_discount(order_discount) if order_discount else None
    has_any = normalized_order is not None

    for line in lines or []:
        if not isinstance(line, dict):
            continue
        raw = line.get("discount")
        if not raw:
            continue
        if is_voucher_sale_line(line):
            raise HTTPException(status_code=400, detail="Voucher sale lines cannot be discounted")
        has_any = True
        if not enabled:
            raise HTTPException(status_code=400, detail="Discounts are not enabled for this event")
        disc = normalize_discount(raw)
        if not disc:
            raise HTTPException(status_code=400, detail="Invalid line discount")
        gross = line_gross_cents(line, articles)
        net = apply_discount_cents(gross, disc)
        if disc["kind"] == "amount" and disc["value"] > gross:
            raise HTTPException(status_code=400, detail="Line discount exceeds line total")

    if normalized_order and not enabled:
        raise HTTPException(status_code=400, detail="Discounts are not enabled for this event")

    if not enabled:
        return None

    if normalized_order:
        from .pricing import order_subtotal_cents

        subtotal = order_subtotal_cents(lines, ev, articles)
        if normalized_order["kind"] == "amount" and normalized_order["value"] > subtotal:
            raise HTTPException(status_code=400, detail="Order discount exceeds subtotal")

    return normalized_order


def discount_hint(discount: dict | None, gross_cents: int, net_cents: int) -> str | None:
    d = normalize_discount(discount)
    if not d or gross_cents <= net_cents:
        return None
    if d["kind"] == "percent":
        return f"Rabatt {d['value']}%"
    off = gross_cents - net_cents
    return f"Rabatt {off / 100:.2f}"


def order_discount_hint(order_discount: dict | None, subtotal_cents: int, net_cents: int) -> str | None:
    d = normalize_discount(order_discount)
    if not d or subtotal_cents <= net_cents:
        return None
    if d["kind"] == "percent":
        return f"Rabatt Bestellung {d['value']}%"
    off = subtotal_cents - net_cents
    return f"Rabatt Bestellung {off / 100:.2f}"
