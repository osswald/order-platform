"""Shared SumUp checkout status helpers."""

from __future__ import annotations

from typing import Any


def normalize_checkout_status(raw: str | None) -> str:
    value = (raw or "pending").strip().lower()
    if value in {"paid", "successful", "success"}:
        return "paid"
    if value in {"failed", "failure"}:
        return "failed"
    if value in {"terminated", "cancelled", "canceled"}:
        return "terminated"
    return "pending"


def transaction_id_from_checkout(payload: dict[str, Any]) -> str | None:
    explicit = payload.get("transaction_id")
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


def apply_checkout_payload(row, payload: dict[str, Any]) -> None:
    row.status = normalize_checkout_status(str(payload.get("status") or row.status))
    txn_id = transaction_id_from_checkout(payload)
    if txn_id:
        row.sumup_transaction_id = txn_id
