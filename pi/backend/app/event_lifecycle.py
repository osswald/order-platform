"""Reconcile Pi local data when event status changes via cloud bundle."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import CollectiveBill, EventOrderCounter, LocalOrder, OutboxEntry, PrintJob


def _event_map(bundle: dict | None) -> dict[int, dict]:
    if not bundle:
        return {}
    out: dict[int, dict] = {}
    for ev in bundle.get("events") or []:
        if isinstance(ev, dict) and ev.get("id") is not None:
            out[int(ev["id"])] = ev
    return out


def purge_event_local_data(db: Session, event_id: int) -> None:
    order_ids = [
        row[0]
        for row in db.query(LocalOrder.id).filter(LocalOrder.event_id == event_id).all()
    ]
    if order_ids:
        db.query(PrintJob).filter(PrintJob.local_order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
    db.query(LocalOrder).filter(LocalOrder.event_id == event_id).delete(synchronize_session=False)
    db.query(OutboxEntry).filter(OutboxEntry.event_id == event_id).delete(synchronize_session=False)
    db.query(CollectiveBill).filter(CollectiveBill.event_id == event_id).delete(synchronize_session=False)
    db.query(EventOrderCounter).filter(EventOrderCounter.event_id == event_id).delete(
        synchronize_session=False
    )
    db.flush()


def reconcile_bundle_lifecycle(db: Session, old_bundle: dict | None, new_bundle: dict | None) -> list[int]:
    """Purge local event data when events leave the bundle or enter production."""
    old_events = _event_map(old_bundle)
    new_events = _event_map(new_bundle)
    purged: list[int] = []

    for event_id, old_ev in old_events.items():
        new_ev = new_events.get(event_id)
        if new_ev is None:
            purge_event_local_data(db, event_id)
            purged.append(event_id)
            continue
        old_status = str(old_ev.get("status") or "").lower()
        new_status = str(new_ev.get("status") or "").lower()
        if old_status == "test" and new_status == "prod":
            purge_event_local_data(db, event_id)
            purged.append(event_id)

    db.commit()
    return purged
