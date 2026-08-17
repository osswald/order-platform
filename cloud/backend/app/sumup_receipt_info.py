"""Normalize SumUp Transactions API payloads into payment-receipt card fields."""

from __future__ import annotations

from typing import Any


def _nonempty_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def receipt_info_from_transaction(payload: dict[str, Any] | None) -> dict[str, str]:
    """Pick printable card-receipt fields from a SumUp transaction resource.

    Returns only non-empty string values suitable for storing on ``SumupCheckout``
    and embedding on Pi payment rows / ESC/POS slips.
    """
    if not isinstance(payload, dict):
        return {}

    card = payload.get("card") if isinstance(payload.get("card"), dict) else {}
    out: dict[str, str] = {}
    mapping = {
        "transaction_code": payload.get("transaction_code"),
        "auth_code": payload.get("auth_code"),
        "card_last_4": card.get("last_4_digits") if isinstance(card, dict) else None,
        "card_type": card.get("type") if isinstance(card, dict) else None,
        "entry_mode": payload.get("entry_mode"),
        "timestamp": payload.get("timestamp"),
        "merchant_code": payload.get("merchant_code"),
    }
    for key, raw in mapping.items():
        text = _nonempty_str(raw)
        if text:
            out[key] = text
    return out
