"""Enqueue operational sync chunks for cloud upload."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from ..models import OutboxEntry


def event_mode_label(status: str | None) -> str:
    return str(status or "config").lower()


def stamp_operational_mode(payload: dict, mode: str | None) -> dict:
    """Attach immutable event mode (test/prod) when the payload does not already have one."""
    out = dict(payload)
    if "mode" not in out and mode:
        out["mode"] = event_mode_label(mode)
    return out


def enrich_payload_for_cloud_sync(
    payload: dict,
    *,
    local_order_id: int,
    session_id: int,
    mode: str | None = None,
) -> dict:
    """Cloud mirror uses local_order_id / session_id for per-order counts in Umsatz."""
    effective_mode = mode or payload.get("mode")
    out = stamp_operational_mode(payload, str(effective_mode) if effective_mode else None)
    out["local_order_id"] = int(local_order_id)
    out["session_id"] = int(session_id)
    return out


def enqueue_submission_sync(db: Session, *, event_id: int, submission_id: int, payload: dict) -> None:
    chunk_id = str(uuid.uuid4())
    db.add(
        OutboxEntry(
            chunk_id=chunk_id,
            entity_type="submission",
            entity_ids_json=json.dumps([submission_id]),
            event_id=event_id,
            payload_json=json.dumps(payload),
            payload_version=1,
            status="pending",
        )
    )


def enqueue_cash_session_sync(db: Session, *, event_id: int, payload: dict) -> None:
    chunk_id = str(uuid.uuid4())
    session_id = int(payload.get("cash_session_id") or 0)
    db.add(
        OutboxEntry(
            chunk_id=chunk_id,
            entity_type="cash_session",
            entity_ids_json=json.dumps([session_id]),
            event_id=event_id,
            payload_json=json.dumps(payload),
            payload_version=1,
            status="pending",
        )
    )


def enqueue_cash_drawer_sync(db: Session, *, event_id: int, payload: dict) -> None:
    chunk_id = str(uuid.uuid4())
    db.add(
        OutboxEntry(
            chunk_id=chunk_id,
            entity_type="cash_drawer",
            entity_ids_json=json.dumps([payload.get("payment_id")]),
            event_id=event_id,
            payload_json=json.dumps(payload),
            payload_version=1,
            status="pending",
        )
    )


def enqueue_payload_sync(db: Session, *, event_id: int, client_order_id: str, payload: dict) -> None:
    """Legacy-shaped enqueue keyed by client_order_id in payload."""
    chunk_id = str(uuid.uuid4())
    db.add(
        OutboxEntry(
            chunk_id=chunk_id,
            entity_type="submission",
            entity_ids_json=json.dumps([client_order_id]),
            event_id=event_id,
            payload_json=json.dumps(payload),
            payload_version=1,
            status="pending",
        )
    )
