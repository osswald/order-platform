"""Build org/event operational snapshot for Pi restore."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .edge_operational_keys import is_open_order_payload, logical_client_order_id
from .models import EdgeCashSession, EdgeKitchenTicketSnapshot, EdgeOrderSnapshot, Event


def _collective_bills_from_orders(open_orders: list[dict]) -> list[dict]:
    by_uuid: dict[str, dict] = {}
    for entry in open_orders:
        payload = entry.get("payload") or {}
        bill_uuid = str(payload.get("collective_bill_uuid") or "").strip()
        if not bill_uuid:
            continue
        by_uuid[bill_uuid] = {
            "uuid": bill_uuid,
            "name": str(payload.get("collective_bill_name") or "Sammelrechnung"),
            "status": "open",
        }
    return list(by_uuid.values())


def build_operational_snapshot_for_events(
    db: Session,
    *,
    organisation_id: int,
    events: list[Event],
) -> dict[str, Any]:
    event_payloads: list[dict[str, Any]] = []
    for ev in events:
        event_id = int(ev.id)
        order_rows = (
            db.query(EdgeOrderSnapshot)
            .filter(
                EdgeOrderSnapshot.organisation_id == organisation_id,
                EdgeOrderSnapshot.event_id == event_id,
            )
            .all()
        )
        open_orders = [
            {
                "client_order_id": row.logical_client_order_id,
                "payload": row.payload if isinstance(row.payload, dict) else {},
            }
            for row in order_rows
            if is_open_order_payload(row.payload if isinstance(row.payload, dict) else {})
        ]

        kitchen_rows = (
            db.query(EdgeKitchenTicketSnapshot)
            .filter(
                EdgeKitchenTicketSnapshot.organisation_id == organisation_id,
                EdgeKitchenTicketSnapshot.event_id == event_id,
            )
            .all()
        )
        open_cids = {o["client_order_id"] for o in open_orders}
        kitchen_tickets = []
        for row in kitchen_rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            logical_cid = logical_client_order_id(payload, fallback=row.logical_client_order_id)
            if logical_cid not in open_cids:
                continue
            kitchen_tickets.append(
                {
                    "client_order_id": logical_cid,
                    "tickets": payload.get("tickets") or [],
                }
            )

        cash_rows = (
            db.query(EdgeCashSession)
            .filter(
                EdgeCashSession.organisation_id == organisation_id,
                EdgeCashSession.event_id == event_id,
                EdgeCashSession.status == "OPEN",
            )
            .all()
        )
        open_cash_sessions = []
        for row in cash_rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            open_cash_sessions.append(
                {
                    "subject_key": row.subject_key,
                    "payload": payload,
                }
            )

        if not open_orders and not kitchen_tickets and not open_cash_sessions:
            continue

        event_payloads.append(
            {
                "event_id": event_id,
                "open_orders": open_orders,
                "collective_bills": _collective_bills_from_orders(open_orders),
                "open_cash_sessions": open_cash_sessions,
                "kitchen_tickets": kitchen_tickets,
            }
        )

    return {"organisation_id": organisation_id, "events": event_payloads}
