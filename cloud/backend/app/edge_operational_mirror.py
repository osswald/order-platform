"""Org/event upsert mirror for Pi operational restore (scenario B)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .edge_operational_keys import (
    is_open_order_payload,
    logical_client_order_id,
)
from .models import EdgeKitchenTicketSnapshot, EdgeOrderSnapshot


def upsert_edge_order_snapshot(
    db: Session,
    *,
    organisation_id: int,
    appliance_id: int,
    event_id: int,
    payload: dict,
) -> None:
    logical_cid = logical_client_order_id(payload)
    if not logical_cid:
        return
    if not is_open_order_payload(payload):
        db.query(EdgeOrderSnapshot).filter(
            EdgeOrderSnapshot.organisation_id == organisation_id,
            EdgeOrderSnapshot.event_id == event_id,
            EdgeOrderSnapshot.logical_client_order_id == logical_cid,
        ).delete(synchronize_session=False)
        return

    now = datetime.now(UTC)
    row = (
        db.query(EdgeOrderSnapshot)
        .filter(
            EdgeOrderSnapshot.organisation_id == organisation_id,
            EdgeOrderSnapshot.event_id == event_id,
            EdgeOrderSnapshot.logical_client_order_id == logical_cid,
        )
        .first()
    )
    fields = {
        "organisation_id": organisation_id,
        "appliance_id": appliance_id,
        "event_id": event_id,
        "logical_client_order_id": logical_cid,
        "payload": dict(payload),
        "updated_at": now,
    }
    if row:
        for key, value in fields.items():
            setattr(row, key, value)
    else:
        db.add(EdgeOrderSnapshot(**fields))


def upsert_edge_kitchen_ticket_snapshot(
    db: Session,
    *,
    organisation_id: int,
    appliance_id: int,
    event_id: int,
    payload: dict,
) -> None:
    logical_cid = logical_client_order_id(payload)
    if not logical_cid:
        return
    tickets = payload.get("tickets") or []
    has_active = any(
        isinstance(t, dict) and str(t.get("status") or "open").lower() != "done" for t in tickets
    )
    if not tickets or not has_active:
        db.query(EdgeKitchenTicketSnapshot).filter(
            EdgeKitchenTicketSnapshot.organisation_id == organisation_id,
            EdgeKitchenTicketSnapshot.event_id == event_id,
            EdgeKitchenTicketSnapshot.logical_client_order_id == logical_cid,
        ).delete(synchronize_session=False)
        return

    now = datetime.now(UTC)
    row = (
        db.query(EdgeKitchenTicketSnapshot)
        .filter(
            EdgeKitchenTicketSnapshot.organisation_id == organisation_id,
            EdgeKitchenTicketSnapshot.event_id == event_id,
            EdgeKitchenTicketSnapshot.logical_client_order_id == logical_cid,
        )
        .first()
    )
    fields = {
        "organisation_id": organisation_id,
        "appliance_id": appliance_id,
        "event_id": event_id,
        "logical_client_order_id": logical_cid,
        "payload": dict(payload),
        "updated_at": now,
    }
    if row:
        for key, value in fields.items():
            setattr(row, key, value)
    else:
        db.add(EdgeKitchenTicketSnapshot(**fields))
