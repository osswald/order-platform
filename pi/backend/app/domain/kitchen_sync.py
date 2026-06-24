"""Kitchen monitor sync payloads for cloud mirror."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from ..models import KitchenTicket, KitchenTicketLine, LocalOrder, OutboxEntry


def build_kitchen_tickets_payload(db: Session, order: LocalOrder) -> dict:
    tickets = (
        db.query(KitchenTicket)
        .filter(KitchenTicket.local_order_id == order.id)
        .order_by(KitchenTicket.id.asc())
        .all()
    )
    ticket_payloads: list[dict] = []
    for ticket in tickets:
        lines = (
            db.query(KitchenTicketLine)
            .filter(KitchenTicketLine.ticket_id == ticket.id)
            .order_by(KitchenTicketLine.line_index.asc(), KitchenTicketLine.id.asc())
            .all()
        )
        ticket_payloads.append(
            {
                "station_uuid": ticket.station_uuid,
                "printer_appliance_id": ticket.printer_appliance_id,
                "status": ticket.status,
                "lines": [
                    {
                        "line_index": int(line.line_index or 0),
                        "line_payload": json.loads(line.line_payload_json),
                        "qty_total": int(line.qty_total or 0),
                        "qty_printed": int(line.qty_printed or 0),
                    }
                    for line in lines
                ],
            }
        )
    return {
        "client_order_id": order.client_order_id,
        "event_id": int(order.event_id),
        "tickets": ticket_payloads,
    }


def enqueue_kitchen_tickets_sync(db: Session, order: LocalOrder) -> None:
    payload = build_kitchen_tickets_payload(db, order)
    for out in (
        db.query(OutboxEntry)
        .filter(
            OutboxEntry.event_id == order.event_id,
            OutboxEntry.entity_type == "kitchen_tickets",
            OutboxEntry.status.in_(("pending", "error")),
        )
        .order_by(OutboxEntry.id.asc())
        .all()
    ):
        try:
            existing = json.loads(out.payload_json)
        except json.JSONDecodeError:
            continue
        if existing.get("client_order_id") == order.client_order_id:
            out.payload_json = json.dumps(payload)
            out.status = "pending"
            return

    db.add(
        OutboxEntry(
            chunk_id=str(uuid.uuid4()),
            entity_type="kitchen_tickets",
            entity_ids_json=json.dumps([order.client_order_id]),
            event_id=order.event_id,
            payload_json=json.dumps(payload),
            payload_version=1,
            status="pending",
        )
    )
