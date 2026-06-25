"""Reconcile Pi local data when event or rental assignment changes."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .models import (
    SyncedBundle,
)
from .models_operational import (
    BundleMeta,
)


def _event_map(bundle: dict | None) -> dict[int, dict]:
    if not bundle:
        return {}
    out: dict[int, dict] = {}
    for ev in bundle.get("events") or []:
        if isinstance(ev, dict) and ev.get("id") is not None:
            out[int(ev["id"])] = ev
    return out


def purge_event_local_data(db: Session, event_id: int) -> None:
    existing = set(inspect(db.get_bind()).get_table_names())

    # Raw SQL deletes avoid ORM bulk-delete edge cases with SQLite.
    for stmt, params in (
        ("DELETE FROM kitchen_ticket_lines WHERE ticket_id IN (SELECT id FROM kitchen_tickets WHERE event_id = :e)", {"e": event_id}),
        ("DELETE FROM kitchen_tickets WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM print_jobs WHERE local_order_id IN (SELECT id FROM order_submissions WHERE event_id = :e)", {"e": event_id}),
        ("DELETE FROM payment_receipts WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM sync_outbox WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM outbox WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM payments WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE event_id = :e)", {"e": event_id}),
        ("DELETE FROM invoices WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM item_transfer_log WHERE item_id IN (SELECT id FROM order_items WHERE event_id = :e)", {"e": event_id}),
        ("DELETE FROM order_items WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM order_submissions WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM order_sessions WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM payment_batches WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM collective_bills WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM cash_session_ledger WHERE cash_session_id IN (SELECT id FROM cash_sessions WHERE event_id = :e)", {"e": event_id}),
        ("DELETE FROM cash_sessions WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM event_order_counters WHERE event_id = :e", {"e": event_id}),
        ("DELETE FROM event_pickup_counters WHERE event_id = :e", {"e": event_id}),
    ):
        table = stmt.split()[2]
        if table in existing:
            db.execute(text(stmt), params)

    db.flush()
    # Bulk deletes do not update the identity map; clear it so later commits
    # cannot accidentally re-flush stale instances.
    db.expunge_all()


def purge_all_operational_data(db: Session) -> None:
    existing = set(inspect(db.get_bind()).get_table_names())
    for table in (
        "kitchen_ticket_lines",
        "kitchen_tickets",
        "print_jobs",
        "payment_receipts",
        "sync_outbox",
        "outbox",
        "payments",
        "invoice_items",
        "invoices",
        "item_transfer_log",
        "order_items",
        "order_submissions",
        "local_orders",
        "order_sessions",
        "payment_batches",
        "collective_bills",
        "cash_session_ledger",
        "cash_sessions",
        "event_order_counters",
        "event_pickup_counters",
        "register_display_states",
    ):
        if table in existing:
            db.execute(text(f"DELETE FROM {table}"))
    db.flush()


def purge_master_cache(db: Session) -> None:
    existing = set(inspect(db.get_bind()).get_table_names())
    if "synced_bundle" in existing:
        db.query(SyncedBundle).delete(synchronize_session=False)
    if "bundle_meta" not in existing:
        db.flush()
        return
    meta = db.query(BundleMeta).filter(BundleMeta.id == 1).first()
    if meta:
        meta.organisation_id = None
        meta.appliance_id = None
        meta.bundle_version = None
        meta.pull_cursor = None
        meta.pull_complete = 0
        meta.last_pull_at = None
    else:
        db.add(BundleMeta(id=1))
    db.flush()


def reconcile_bundle_lifecycle(db: Session, old_bundle: dict | None, new_bundle: dict | None) -> list[int]:
    old_org = (old_bundle or {}).get("organisation_id")
    new_org = (new_bundle or {}).get("organisation_id")
    old_app = (old_bundle or {}).get("appliance_id")
    new_app = (new_bundle or {}).get("appliance_id")
    if old_org is not None and new_org is not None and int(old_org) != int(new_org):
        purge_all_operational_data(db)
        purged: list[int] = []
    elif old_app is not None and new_app is not None and int(old_app) != int(new_app):
        purge_all_operational_data(db)
        purged = []
    else:
        purged = []

    old_events = _event_map(old_bundle)
    new_events = _event_map(new_bundle)

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

    existing = set(inspect(db.get_bind()).get_table_names())
    if "bundle_meta" in existing:
        meta = db.query(BundleMeta).filter(BundleMeta.id == 1).first()
        if not meta:
            meta = BundleMeta(id=1)
            db.add(meta)
        if new_bundle:
            if new_bundle.get("organisation_id") is not None:
                meta.organisation_id = int(new_bundle["organisation_id"])
            if new_bundle.get("appliance_id") is not None:
                meta.appliance_id = int(new_bundle["appliance_id"])
            meta.bundle_version = str(new_bundle.get("bundle_version") or meta.bundle_version or "")
            meta.pull_complete = 1

    # Defensive final sweep on purged events to avoid stale identity-map
    # instances being flushed back by SQLAlchemy in long-lived sessions.
    for event_id in purged:
        if "order_submissions" in existing:
            db.execute(text("DELETE FROM order_submissions WHERE event_id = :e"), {"e": event_id})
        if "sync_outbox" in existing:
            db.execute(text("DELETE FROM sync_outbox WHERE event_id = :e"), {"e": event_id})
        if "payment_batches" in existing:
            db.execute(text("DELETE FROM payment_batches WHERE event_id = :e"), {"e": event_id})

    db.commit()
    db.expire_all()
    return purged


def purge_on_unpair(db: Session) -> None:
    purge_all_operational_data(db)
    purge_master_cache(db)
    db.commit()
