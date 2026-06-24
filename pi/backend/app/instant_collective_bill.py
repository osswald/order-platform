"""Ensure event instant-mode Sammelrechnung exists locally."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import CollectiveBill


def instant_collective_bill_config(ev: dict) -> tuple[str, str] | None:
    if (ev.get("payment_mode") or "pay_later").lower() != "instant":
        return None
    bill_uuid = str(ev.get("instant_collective_bill_uuid") or "").strip()
    bill_name = str(ev.get("instant_collective_bill_name") or "").strip() or "Sammelrechnung"
    if not bill_uuid:
        return None
    return bill_uuid, bill_name


def ensure_instant_collective_bill(db: Session, ev: dict) -> CollectiveBill | None:
    cfg = instant_collective_bill_config(ev)
    if not cfg:
        return None
    bill_uuid, bill_name = cfg
    event_id = int(ev["id"])
    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.uuid == bill_uuid, CollectiveBill.event_id == event_id)
        .first()
    )
    if bill:
        if bill_name and bill.name != bill_name:
            bill.name = bill_name
        return bill
    bill = CollectiveBill(uuid=bill_uuid, event_id=event_id, name=bill_name)
    db.add(bill)
    db.flush()
    return bill


def ensure_instant_collective_bills_for_bundle(db: Session, bundle: dict) -> None:
    for ev in bundle.get("events") or []:
        if isinstance(ev, dict):
            ensure_instant_collective_bill(db, ev)
