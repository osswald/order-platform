"""Shared SumUp checkout status helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def unwrap_sumup_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten Solo Cloud API envelopes ``{"data": {...}}`` while keeping flat payloads."""
    data = payload.get("data")
    if isinstance(data, dict) and data:
        merged = dict(payload)
        merged.update(data)
        return merged
    return payload


def normalize_checkout_status(raw: str | None) -> str:
    value = (raw or "pending").strip().lower()
    if value in {"paid", "successful", "success"}:
        return "paid"
    if value in {"failed", "failure"}:
        return "failed"
    if value in {"terminated", "cancelled", "canceled"}:
        return "terminated"
    return "pending"


def _parse_sumup_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def checkout_expired(payload: dict[str, Any], *, now: datetime | None = None) -> bool:
    """Solo checkouts include ``valid_until``; SumUp may leave status pending after expiry."""
    payload = unwrap_sumup_data(payload)
    expires_at = _parse_sumup_datetime(payload.get("valid_until"))
    if expires_at is None:
        return False
    current = now or datetime.now(UTC)
    return expires_at <= current


def status_from_checkout_payload(payload: dict[str, Any], *, now: datetime | None = None) -> str:
    payload = unwrap_sumup_data(payload)
    priority = {"paid": 3, "failed": 2, "terminated": 2, "pending": 0}
    best = "pending"
    for key in ("status", "payment_status"):
        raw = payload.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        normalized = normalize_checkout_status(raw)
        if priority[normalized] > priority[best]:
            best = normalized
    if best == "pending" and checkout_expired(payload, now=now):
        return "terminated"
    return best


def transaction_id_from_checkout(payload: dict[str, Any]) -> str | None:
    payload = unwrap_sumup_data(payload)
    for key in ("client_transaction_id", "transaction_id"):
        explicit = payload.get(key)
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
    transactions = payload.get("transactions")
    if not isinstance(transactions, list):
        return None
    for item in transactions:
        if not isinstance(item, dict):
            continue
        txn_id = item.get("id") or item.get("transaction_id")
        if isinstance(txn_id, str) and txn_id.strip():
            return txn_id.strip()
    return None


def checkout_id_from_payload(payload: dict[str, Any]) -> str | None:
    payload = unwrap_sumup_data(payload)
    for key in ("checkout_id", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def apply_checkout_payload(row, payload: dict[str, Any], *, now: datetime | None = None) -> None:
    payload = unwrap_sumup_data(payload)
    row.status = status_from_checkout_payload(payload, now=now)
    txn_id = transaction_id_from_checkout(payload)
    if txn_id:
        row.sumup_transaction_id = txn_id
