"""Move open order lines between tables and collective bills."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from .domain.sessions import ensure_order_session
from .domain.sync_enqueue import enrich_payload_for_cloud_sync, enqueue_payload_sync
from .models import CollectiveBill, LocalOrder
from .order_line_utils import merge_lines_into_list, take_selections_from_orders


def _load_payload(order: LocalOrder) -> dict:
    return json.loads(order.payload_json)


def _save_order_payload(db: Session, order: LocalOrder, payload: dict, sync_outbox) -> None:
    order.payload_json = json.dumps(payload)
    if order.payment_status == "open":
        sync_outbox(db, order, payload)


def take_from_orders(db: Session, orders: list, selections: list[dict], sync_outbox) -> list[dict]:
    def load_payload(order):
        return _load_payload(order)

    def save_payload(order, payload):
        if payload.get("lines"):
            order.payment_status = "open"
            _save_order_payload(db, order, payload, sync_outbox)
        else:
            order.payment_status = "paid"
            payload["payment_status"] = "paid"
            order.payload_json = json.dumps(payload)
            sync_outbox(db, order, payload)

    return take_selections_from_orders(
        orders,
        selections,
        load_payload=load_payload,
        save_payload=save_payload,
    )


def append_lines_to_table(
    db: Session,
    *,
    ev: dict,
    event_id: int,
    target_table: int,
    waiter_uuid: str | None,
    lines: list[dict],
    lines_with_station,
    sync_outbox,
) -> None:
    target_orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.table_number == target_table,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.desc())
        .all()
    )
    stamped = lines_with_station(ev, lines)
    if target_orders:
        order = target_orders[0]
        payload = _load_payload(order)
        existing = payload.get("lines") or []
        merge_lines_into_list(existing, stamped)
        payload["lines"] = existing
        _save_order_payload(db, order, payload, sync_outbox)
    else:
        cid = f"xfer-{target_table}-{uuid.uuid4().hex[:12]}"
        payload = {
            "client_order_id": cid,
            "event_id": event_id,
            "table_number": target_table,
            "waiter_uuid": waiter_uuid,
            "lines": stamped,
            "payments": [],
            "payment_status": "open",
            "transferred": True,
        }
        session_id = ensure_order_session(
            db,
            event_id=event_id,
            table_number=target_table,
            waiter_uuid=waiter_uuid,
            order_source="waiter",
        )
        order = LocalOrder(
            session_id=session_id,
            client_order_id=cid,
            event_id=event_id,
            table_number=target_table,
            collective_bill_id=None,
            waiter_uuid=waiter_uuid,
            payment_status="open",
            payload_json=json.dumps(payload),
            print_status="done",
        )
        db.add(order)
        db.flush()
        enqueue_payload_sync(
            db,
            event_id=event_id,
            client_order_id=cid,
            payload=enrich_payload_for_cloud_sync(payload, local_order_id=order.id, session_id=session_id),
        )


def append_lines_to_collective(
    db: Session,
    *,
    ev: dict,
    bill: CollectiveBill,
    event_id: int,
    waiter_uuid: str | None,
    lines: list[dict],
    lines_with_station,
    sync_outbox,
) -> None:
    target_orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.desc())
        .all()
    )
    stamped = lines_with_station(ev, lines)
    bill_meta = {
        "collective_bill_uuid": bill.uuid,
        "collective_bill_name": bill.name,
        "table_number": None,
    }
    if target_orders:
        order = target_orders[0]
        payload = _load_payload(order)
        existing = payload.get("lines") or []
        merge_lines_into_list(existing, stamped)
        payload["lines"] = existing
        payload.update(bill_meta)
        _save_order_payload(db, order, payload, sync_outbox)
    else:
        cid = f"coll-{bill.id}-{uuid.uuid4().hex[:12]}"
        payload = {
            "client_order_id": cid,
            "event_id": event_id,
            **bill_meta,
            "waiter_uuid": waiter_uuid,
            "lines": stamped,
            "payments": [],
            "payment_status": "open",
        }
        session_id = ensure_order_session(
            db,
            event_id=event_id,
            table_number=None,
            waiter_uuid=waiter_uuid,
            order_source="waiter",
        )
        order = LocalOrder(
            session_id=session_id,
            client_order_id=cid,
            event_id=event_id,
            table_number=0,
            collective_bill_id=bill.id,
            waiter_uuid=waiter_uuid,
            payment_status="open",
            payload_json=json.dumps(payload),
            print_status="done",
        )
        db.add(order)
        db.flush()
        enqueue_payload_sync(
            db,
            event_id=event_id,
            client_order_id=cid,
            payload=enrich_payload_for_cloud_sync(payload, local_order_id=order.id, session_id=session_id),
        )
