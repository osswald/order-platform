"""Pi ↔ cloud sync: push outbox, pull bundle, reconcile local stock."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from .bundle_cache import get_bundle_dict_raw
from .cloud_client import (
    CloudConfigError,
    ConditionalGetResult,
    _resolve_config,
    edge_http_client,
    fetch_bundle,
    fetch_operational_snapshot,
    submit_operational_chunk,
)
from .escpos_render import clear_receipt_logo_cache
from .event_lifecycle import reconcile_bundle_lifecycle
from .models import OutboxEntry, SyncedBundle
from .operational_restore import needs_operational_restore, restore_operational_snapshot
from .ota_freeze import write_ota_freeze_from_bundle
from .screensaver_sync import sync_screensaver_images
from .stock import apply_stock_to_bundle, persist_catalogue_bundle, persist_local_stock

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
    "last_restore_check_at": None,
    "snapshot_etag": None,
}


def bundle_content_fingerprint(payload: dict[str, Any]) -> str:
    """Stable hash of bundle content excluding request-volatile ``server_time``."""
    body = {k: v for k, v in payload.items() if k != "server_time"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_cloud_configured() -> bool:
    base, cid, secret = _resolve_config()
    return bool(base and cid and secret)


def is_push_enabled() -> bool:
    val = os.getenv("SYNC_PUSH_ENABLED", "1").strip().lower()
    return val not in ("0", "false", "no")


def is_restore_enabled() -> bool:
    val = os.getenv("RESTORE_FROM_CLOUD", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def restore_check_max_idle_seconds() -> int:
    raw = os.getenv("SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS", "300").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 300


def pending_outbox_count(db: Session) -> int:
    return (
        db.query(OutboxEntry)
        .filter(OutboxEntry.status.in_(("pending", "error")))
        .count()
    )


def should_check_operational_restore(
    db: Session,
    *,
    bundle_changed: bool,
    force: bool = False,
) -> bool:
    """Whether this cycle should fetch the operational snapshot."""
    if not is_restore_enabled():
        return False
    if force or bundle_changed:
        return True
    if pending_outbox_count(db) > 0:
        return True
    max_idle = restore_check_max_idle_seconds()
    if max_idle <= 0:
        return True
    last_raw = sync_status.get("last_restore_check_at")
    if not last_raw:
        return True
    try:
        last = datetime.fromisoformat(str(last_raw).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except ValueError:
        return True
    age = (datetime.now(UTC) - last).total_seconds()
    return age >= max_idle


async def push_outbox(
    db: Session,
    *,
    retry_errors: bool = True,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
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
                client=client,
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


async def pull_bundle(
    db: Session,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Download bundle from cloud into SyncedBundle (conditional GET when possible)."""
    old_bundle = get_bundle_dict_raw(db)
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    prior_etag = (row.etag if row else None) or None
    # Fingerprint the durable catalogue baseline (not effective overlay) so local
    # stock deductions do not force a false "body changed" on no-ETag fallback.
    prior_fp = None
    if row and row.json_body:
        try:
            catalogue = json.loads(row.json_body)
            if isinstance(catalogue, dict):
                prior_fp = bundle_content_fingerprint(catalogue)
        except json.JSONDecodeError:
            prior_fp = None

    result: ConditionalGetResult = await fetch_bundle(client=client, etag=prior_etag)

    if result.not_modified:
        data = old_bundle if isinstance(old_bundle, dict) else {}
        if row is not None and result.etag and result.etag != row.etag:
            row.etag = result.etag
            db.commit()
        event_count = len(data.get("events", [])) if isinstance(data, dict) else 0
        return {
            "ok": True,
            "event_count": event_count,
            "bundle": data,
            "purged_event_ids": [],
            "bundle_changed": False,
            "not_modified": True,
        }

    assert result.data is not None
    data = result.data
    new_fp = bundle_content_fingerprint(data)
    identical = prior_fp is not None and new_fp == prior_fp

    if identical:
        if row is not None and result.etag and result.etag != row.etag:
            row.etag = result.etag
            db.commit()
        # Body unchanged — keep warm process cache (old_bundle already loaded).
        event_count = len(data.get("events", []))
        return {
            "ok": True,
            "event_count": event_count,
            "bundle": data,
            "purged_event_ids": [],
            "bundle_changed": False,
            "not_modified": False,
        }

    persist_catalogue_bundle(db, data, etag=result.etag)
    db.commit()
    # Bundle may replace event logos; drop prepared rasters so the next slip uses new art.
    clear_receipt_logo_cache()
    write_ota_freeze_from_bundle(data if isinstance(data, dict) else None)
    purged = reconcile_bundle_lifecycle(db, old_bundle, data)
    event_count = len(data.get("events", []))
    return {
        "ok": True,
        "event_count": event_count,
        "bundle": data,
        "purged_event_ids": purged,
        "bundle_changed": True,
        "not_modified": False,
    }


def reapply_pending_stock(db: Session, bundle: dict | None = None) -> bool:
    """Re-decrement stock for orders not yet acknowledged by cloud (after a pull).

    Persists via local stock overlay (does not rewrite catalogue JSON).
    Returns True when any monitored stock was applied and persisted.
    """
    data = bundle if bundle is not None else get_bundle_dict_raw(db)
    if not data or data.get("organisation_id") is None:
        return False
    rows = (
        db.query(OutboxEntry)
        .filter(OutboxEntry.status.in_(("pending", "error")))
        .order_by(OutboxEntry.id.asc())
        .all()
    )
    if not rows:
        return False
    touched_events: set[int] = set()
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
        except json.JSONDecodeError:
            continue
        lines = payload.get("lines") or []
        if lines:
            apply_stock_to_bundle(data, row.event_id, lines)
            touched_events.add(int(row.event_id))
    if not touched_events:
        return False
    persist_local_stock(db, data, event_ids=touched_events)
    return True


async def pull_and_restore(
    db: Session,
    *,
    client: httpx.AsyncClient | None = None,
    force_restore_check: bool = False,
) -> dict[str, Any]:
    """Pull bundle from cloud, reapply stock, and optionally restore operational snapshot."""
    pull_result = await pull_bundle(db, client=client)
    bundle_changed = bool(pull_result.get("bundle_changed"))
    # Only re-stamp stock onto a fresh cloud catalogue baseline — never on 304 /
    # identical-body where the local effective bundle already includes deductions.
    if bundle_changed:
        if reapply_pending_stock(db, pull_result.get("bundle")):
            db.commit()
        # If reapply was a no-op, catalogue commit from pull already landed.

    # Screensaver sync: run after every successful pull (incl. 304) so GC/download
    # still happen when only media changed independently — manifest rides the bundle.
    try:
        pull_result["screensaver"] = await sync_screensaver_images(
            pull_result.get("bundle") if isinstance(pull_result.get("bundle"), dict) else None,
            client=client,
        )
    except Exception as exc:  # noqa: BLE001 — sync must not fail the whole pull
        pull_result["screensaver"] = {"errors": [{"error": str(exc)}]}

    if not should_check_operational_restore(
        db,
        bundle_changed=bundle_changed,
        force=force_restore_check,
    ):
        pull_result["restore_deferred"] = True
        return pull_result

    now = datetime.now(UTC).isoformat()
    sync_status["last_restore_check_at"] = now

    if not is_restore_enabled():
        return pull_result

    try:
        snap: ConditionalGetResult = await fetch_operational_snapshot(
            client=client,
            etag=sync_status.get("snapshot_etag"),
        )
        if snap.etag:
            sync_status["snapshot_etag"] = snap.etag
        if snap.not_modified:
            pull_result["restore_skipped"] = "not_modified"
            return pull_result

        assert snap.data is not None
        snapshot = snap.data
        bundle = pull_result.get("bundle")
        if needs_operational_restore(db, snapshot):
            restore_summary = restore_operational_snapshot(db, snapshot, bundle)
            pull_result["restore"] = restore_summary
            if bundle:
                if reapply_pending_stock(db, bundle):
                    db.commit()
        else:
            pull_result["restore_skipped"] = "fingerprint_match"
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
        async with edge_http_client() as client:
            try:
                pull_result = await pull_and_restore(db, client=client)
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
                    push_result = await push_outbox(db, retry_errors=True, client=client)
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
    except CloudConfigError as e:
        last_error = str(e)

    sync_status["last_cycle_at"] = now
    sync_status["pending_outbox_count"] = pending_outbox_count(db)
    sync_status["last_error"] = last_error
    if last_error:
        summary["error"] = last_error
    return summary
