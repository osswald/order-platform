"""Verify waiter / cash-register PINs against synced bundle hashes."""

from typing import Any

from .security import verify_password


def _is_pin_hash(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$")) and len(value) > 20


def verify_stored_pin(plain: str, stored: str | None) -> bool:
    if not stored:
        return False
    if _is_pin_hash(stored):
        try:
            return verify_password(plain, stored)
        except Exception:
            return False
    return plain == stored


def _event_from_bundle(bundle: dict[str, Any], event_id: int) -> dict[str, Any] | None:
    for ev in bundle.get("events") or []:
        if int(ev.get("id") or 0) == int(event_id):
            return ev
    return None


def verify_waiter_pin(
    bundle: dict[str, Any],
    *,
    event_id: int,
    waiter_uuid: str,
    pin: str,
) -> bool:
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        return False
    for w in (ev.get("configuration") or {}).get("event_waiters") or []:
        if str(w.get("uuid")) != str(waiter_uuid):
            continue
        stored = w.get("pin_hash") or w.get("pin")
        return verify_stored_pin(pin, stored)
    return False


def verify_register_pin(
    bundle: dict[str, Any],
    *,
    event_id: int,
    register_uuid: str,
    pin: str,
) -> bool:
    ev = _event_from_bundle(bundle, event_id)
    if not ev:
        return False
    for reg in (ev.get("configuration") or {}).get("cash_registers") or []:
        if str(reg.get("uuid")) != str(register_uuid):
            continue
        stored = reg.get("pin_hash") or reg.get("pin")
        return verify_stored_pin(pin, stored)
    return False
