"""Pi ↔ cloud sync: push outbox, pull bundle, reconcile local stock."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .cloud_client import CloudConfigError, _resolve_config, fetch_bundle, submit_order
from .event_lifecycle import reconcile_bundle_lifecycle
from .models import OutboxEntry, SyncedBundle
from .stock import apply_stock_to_bundle, save_bundle

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
}


def is_cloud_configured() -> bool:
    base, cid, secret = _resolve_config()
    return bool(base and cid and secret)


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
            await submit_order(row.client_order_id, row.event_id, payload)
            row.status = "sent"
            row.last_error = None
            sent += 1
        except CloudConfigError:
            raise
        except Exception as e:
            row.status = "error"
            row.last_error = str(e)[:2000]
            errors.append({"client_order_id": row.client_order_id, "error": str(e)})
        db.commit()
    return {"sent": sent, "errors": errors}


async def pull_bundle(db: Session) -> dict[str, Any]:
    """Download bundle from cloud into SyncedBundle."""
    old_bundle = _get_bundle_dict_raw(db)
    data = await fetch_bundle()
    body = json.dumps(data)
    now = datetime.now(timezone.utc)
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row:
        db.add(SyncedBundle(id=1, json_body=body, updated_at=now))
    else:
        row.json_body = body
        row.updated_at = now
    db.commit()
    purged = reconcile_bundle_lifecycle(db, old_bundle, data)
    event_count = len(data.get("events", []))
    return {"ok": True, "event_count": event_count, "bundle": data, "purged_event_ids": purged}


def _get_bundle_dict_raw(db: Session) -> dict | None:
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if not row or not row.json_body:
        return None
    data = json.loads(row.json_body)
    return data if isinstance(data, dict) else None


def reapply_pending_stock(db: Session, bundle: dict | None = None) -> None:
    """Re-decrement stock for orders not yet acknowledged by cloud (after a pull)."""
    data = bundle if bundle is not None else _get_bundle_dict_raw(db)
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


async def run_sync_cycle(db: Session) -> dict[str, Any]:
    """Pull bundle, reconcile lifecycle, push outbox, reapply local stock."""
    now = datetime.now(timezone.utc).isoformat()
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
        pull_result = await pull_bundle(db)
        summary["pull_ok"] = True
        summary["event_count"] = pull_result["event_count"]
        summary["purged_event_ids"] = pull_result.get("purged_event_ids") or []
        sync_status["last_pull_at"] = now
        sync_status["last_event_count"] = pull_result["event_count"]
        reapply_pending_stock(db, pull_result.get("bundle"))
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
        push_result = await push_outbox(db, retry_errors=True)
        summary["push_sent"] = push_result["sent"]
        summary["push_errors"] = push_result["errors"]
        sync_status["last_push_sent"] = push_result["sent"]
        if push_result["errors"]:
            last_error = push_result["errors"][0].get("error")
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
