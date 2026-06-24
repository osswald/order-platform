"""Stable keys for org/event operational mirror (cross-appliance takeover)."""

from __future__ import annotations


def logical_client_order_id(payload: dict, *, fallback: str | None = None) -> str:
    cid = (payload or {}).get("client_order_id") or fallback
    return str(cid or "").strip()


def cash_session_subject_key(payload: dict) -> str | None:
    subject_type = str((payload or {}).get("subject_type") or "waiter").strip().lower()
    if subject_type == "cash_register":
        reg = (payload or {}).get("cash_register_uuid")
        return f"cash_register:{reg}" if reg else None
    waiter = (payload or {}).get("waiter_uuid")
    return f"waiter:{waiter}" if waiter else None


def kitchen_ticket_match_key(*, station_uuid: str, printer_appliance_id: int | None) -> str:
    pid = int(printer_appliance_id) if printer_appliance_id is not None else 0
    return f"{station_uuid}:{pid}"


def is_open_order_payload(payload: dict) -> bool:
    if str((payload or {}).get("payment_status") or "open").lower() == "paid":
        return False
    for ln in (payload or {}).get("lines") or []:
        if isinstance(ln, dict) and ln.get("article_id") is not None and int(ln.get("qty") or 0) > 0:
            return True
    return False


def snapshot_has_lines(payload: dict) -> bool:
    for ln in (payload or {}).get("lines") or []:
        if isinstance(ln, dict) and ln.get("article_id") is not None:
            return True
    return False
