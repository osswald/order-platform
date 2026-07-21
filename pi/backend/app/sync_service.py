"""Pi ↔ cloud sync: push outbox, pull bundle, reconcile local stock."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from .bundle_cache import get_bundle_dict_raw
from .cloud_client import (
    CloudConfigError,
    _resolve_config,
    fetch_bundle,
    fetch_operational_snapshot,
    submit_operational_chunk,
)
from .event_lifecycle import reconcile_bundle_lifecycle
from .models import OutboxEntry, SyncedBundle
from .operational_restore import needs_operational_restore, restore_operational_snapshot
from .ota_freeze import write_ota_freeze_from_bundle
from .stock import apply_stock_to_bundle, save_bundle

# Serialize pull/push with the background sync worker (SQLite).
sync_cycle_lock = asyncio.Lock()

log = logging.getLogger(__name__)

# Updated by run_sync_cycle / sync_worker for GET /v1/sync/status
sync_status: dict[str, Any] = {
    "configured": False,
    "auto_sync_enabled": True,
    "last_cycle_at": None,
    "last_push_sent": 0,
    "last_pull_at": None,
    "last_event_count": None,
    "pending_outbox_count": 0,
    "last_error": None,
    "last_restore_at": None,
    "last_restore_summary": None,
}


def is_cloud_configured() -> bool:
    base, cid, secret = _resolve_config()
    return bool(base and cid and secret)


def is_push_enabled() -> bool:
    val = os.getenv("SYNC_PUSH_ENABLED", "1").strip().lower()
    return val not in ("0", "false", "no")


def is_restore_enabled() -> bool:
    val = os.getenv("RESTORE_FROM_CLOUD", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def pending_outbox_count(db: Session) -> int:
    return (
        db.query(OutboxEntry)
        .filter(OutboxEntry.status.in_(("pending", "error")))
        .count()
    )


async def push_outbox(db: Session, *, retry_errors: bool = True) -> dict[str, Any]:
    """Upload pending (and optionally failed) outbox entries to cloud."""
    statuses = ["pending"]
    if retry_errors:
        statuses.append("error")
    rows = (
        db.query(OutboxEntry)
        .filter(OutboxEntry.status.in_(statuses))
        .order_by(OutboxEntry.id.asc())
        .all()
    )
    sent = 0
    errors: list[dict[str, str]] = []
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
            await submit_operational_chunk(
                chunk_id=row.chunk_id,
                event_id=row.event_id,
                entity_type=row.entity_type,
                payload=payload,
            )
            row.status = "acked"
            row.acked_at = datetime.now(UTC)
            row.last_error = None
            sent += 1
        except CloudConfigError:
            raise
        except Exception as e:
            row.status = "error"
            row.attempt_count = int(row.attempt_count or 0) + 1
            row.last_error = str(e)[:2000]
            errors.append({"chunk_id": row.chunk_id, "error": str(e)})
    db.commit()
    return {"sent": sent, "errors": errors}


async def pull_bundle(db: Session) -> dict[str, Any]:
    """Download bundle from cloud into SyncedBundle."""
    old_bundle = get_bundle_dict_raw(db)
    data = await fetch_bundle()
    body = json.dumps(data)
    now = datetime.now(UTC)
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row:
        db.add(SyncedBundle(id=1, json_body=body, updated_at=now))
    else:
        row.json_body = body
        row.updated_at = now
    db.commit()
    write_ota_freeze_from_bundle(data if isinstance(data, dict) else None)
    purged = reconcile_bundle_lifecycle(db, old_bundle, data)
    event_count = len(data.get("events", []))
    return {"ok": True, "event_count": event_count, "bundle": data, "purged_event_ids": purged}


def reapply_pending_stock(db: Session, bundle: dict | None = None) -> None:
    """Re-decrement stock for orders not yet acknowledged by cloud (after a pull)."""
    data = bundle if bundle is not None else get_bundle_dict_raw(db)
    if not data or data.get("organisation_id") is None:
        return
    rows = (
        db.query(OutboxEntry)
        .filter(OutboxEntry.status.in_(("pending", "error")))
        .order_by(OutboxEntry.id.asc())
        .all()
    )
    if not rows:
        return
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
        except json.JSONDecodeError:
            continue
        lines = payload.get("lines") or []
        if lines:
            apply_stock_to_bundle(data, row.event_id, lines)
    save_bundle(db, data)


async def pull_and_restore(db: Session) -> dict[str, Any]:
    """Pull bundle from cloud, reapply stock, and optionally restore operational snapshot."""
    pull_result = await pull_bundle(db)
    reapply_pending_stock(db, pull_result.get("bundle"))
    if is_restore_enabled():
        try:
            snapshot = await fetch_operational_snapshot()
            bundle = pull_result.get("bundle")
            if needs_operational_restore(db, snapshot):
                restore_summary = restore_operational_snapshot(db, snapshot, bundle)
                pull_result["restore"] = restore_summary
                if bundle:
                    reapply_pending_stock(db, bundle)
        except Exception as e:
            log.warning("operational restore failed: %s", e)
            pull_result["restore_failed"] = str(e)[:2000]
    return pull_result


async def run_sync_cycle(db: Session) -> dict[str, Any]:
    """Pull bundle, reconcile lifecycle, push outbox, reapply local stock."""
    now = datetime.now(UTC).isoformat()
    sync_status["configured"] = is_cloud_configured()
    sync_status["pending_outbox_count"] = pending_outbox_count(db)

    if not is_cloud_configured():
        return {"skipped": True, "reason": "cloud_not_configured"}

    summary: dict[str, Any] = {
        "skipped": False,
        "push_sent": 0,
        "push_errors": [],
        "pull_ok": False,
        "event_count": 0,
        "purged_event_ids": [],
    }
    last_error: str | None = None

    try:
        pull_result = await pull_and_restore(db)
        summary["pull_ok"] = True
        summary["event_count"] = pull_result["event_count"]
        summary["purged_event_ids"] = pull_result.get("purged_event_ids") or []
        sync_status["last_pull_at"] = now
        sync_status["last_event_count"] = pull_result["event_count"]
        if pull_result.get("restore"):
            summary["restore"] = pull_result["restore"]
            sync_status["last_restore_at"] = now
            sync_status["last_restore_summary"] = pull_result["restore"]
        if pull_result.get("restore_failed"):
            summary["restore_failed"] = pull_result["restore_failed"]
    except CloudConfigError as e:
        last_error = str(e)
        sync_status["last_error"] = last_error
        sync_status["last_cycle_at"] = now
        return {**summary, "error": last_error}
    except Exception as e:
        last_error = str(e)
        log.warning("sync pull failed: %s", e)
        summary["pull_failed"] = True

    try:
        if is_push_enabled():
            push_result = await push_outbox(db, retry_errors=True)
            summary["push_sent"] = push_result["sent"]
            summary["push_errors"] = push_result["errors"]
            sync_status["last_push_sent"] = push_result["sent"]
            if push_result["errors"]:
                last_error = push_result["errors"][0].get("error")
        else:
            summary["push_skipped"] = True
    except CloudConfigError as e:
        last_error = str(e)
    except Exception as e:
        last_error = str(e)
        log.warning("sync push failed: %s", e)
        summary["push_failed"] = True

    sync_status["last_cycle_at"] = now
    sync_status["pending_outbox_count"] = pending_outbox_count(db)
    sync_status["last_error"] = last_error
    if last_error:
        summary["error"] = last_error
    return summary
