"""Restore Pi operational SQLite from cloud org/event snapshot (scenario B)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from .bundle_cache import event_from_bundle
from .domain.sessions import ensure_order_session
from .models import (
    EventOrderCounter,
    EventPickupCounter,
    KitchenTicket,
    KitchenTicketLine,
    LocalOrder,
    OutboxEntry,
)
from .models_operational import CashSession, CashSessionLedger, PaymentBatch
from .print_worker import group_lines_by_station
from .printer_routing import printer_in_kitchen_monitor, subgroup_lines_by_printer
from .stock import apply_stock_to_bundle, save_bundle

log = logging.getLogger(__name__)


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except ValueError:
        return None


def _local_open_fingerprint(db: Session, event_id: int) -> str:
    rows = (
        db.query(LocalOrder)
        .filter(LocalOrder.event_id == event_id, LocalOrder.payment_status == "open")
        .order_by(LocalOrder.client_order_id.asc())
        .all()
    )
    parts: list[str] = []
    for row in rows:
        payload = json.loads(row.payload_json or "{}")
        parts.append(f"{row.client_order_id}:{hash(json.dumps(payload, sort_keys=True))}")
    tickets = (
        db.query(KitchenTicket)
        .join(LocalOrder, LocalOrder.id == KitchenTicket.local_order_id)
        .filter(KitchenTicket.event_id == event_id, KitchenTicket.status != "done")
        .order_by(KitchenTicket.id.asc())
        .all()
    )
    for ticket in tickets:
        parts.append(f"kt:{ticket.id}:{ticket.status}")
    return "|".join(parts)


def _cloud_fingerprint(event_snap: dict) -> str:
    parts: list[str] = []
    for entry in event_snap.get("open_orders") or []:
        cid = entry.get("client_order_id")
        payload = entry.get("payload") or {}
        parts.append(f"{cid}:{hash(json.dumps(payload, sort_keys=True))}")
    for entry in event_snap.get("kitchen_tickets") or []:
        cid = entry.get("client_order_id")
        parts.append(f"kt:{cid}:{hash(json.dumps(entry.get('tickets') or [], sort_keys=True))}")
    return "|".join(sorted(parts))


def needs_operational_restore(db: Session, snapshot: dict) -> bool:
    for event_snap in snapshot.get("events") or []:
        event_id = int(event_snap.get("event_id") or 0)
        if not event_id:
            continue
        if not (
            event_snap.get("open_orders")
            or event_snap.get("kitchen_tickets")
            or event_snap.get("open_cash_sessions")
        ):
            continue
        if _local_open_fingerprint(db, event_id) != _cloud_fingerprint(event_snap):
            return True
    return False


def _upsert_collective_bill(db: Session, *, event_id: int, bill: dict) -> PaymentBatch | None:
    bill_uuid = str(bill.get("uuid") or "").strip()
    if not bill_uuid:
        return None
    row = db.query(PaymentBatch).filter(PaymentBatch.uuid == bill_uuid).first()
    if not row:
        row = PaymentBatch(
            uuid=bill_uuid,
            event_id=event_id,
            name=str(bill.get("name") or "Sammelrechnung"),
            status=str(bill.get("status") or "open"),
        )
        db.add(row)
        db.flush()
    else:
        row.name = str(bill.get("name") or row.name)
        row.status = str(bill.get("status") or row.status)
    return row


def _restore_order(
    db: Session,
    *,
    event_id: int,
    client_order_id: str,
    payload: dict,
    bill_by_uuid: dict[str, PaymentBatch],
) -> LocalOrder:
    bill_uuid = str(payload.get("collective_bill_uuid") or "").strip()
    collective_bill_id = None
    if bill_uuid and bill_uuid in bill_by_uuid:
        collective_bill_id = bill_by_uuid[bill_uuid].id

    table_number = int(payload.get("table_number") or 0)
    order_source = str(payload.get("order_source") or "waiter")
    session_id = ensure_order_session(
        db,
        event_id=event_id,
        table_number=table_number if table_number > 0 else None,
        waiter_uuid=payload.get("waiter_uuid"),
        order_source=order_source,
        cash_register_uuid=payload.get("cash_register_uuid"),
        pickup_code=payload.get("pickup_code"),
    )

    row = db.query(LocalOrder).filter(LocalOrder.client_order_id == client_order_id).first()
    ready_at = _parse_dt(payload.get("ready_at"))
    if not row:
        row = LocalOrder(
            session_id=session_id,
            client_order_id=client_order_id,
            event_id=event_id,
            table_number=table_number,
            waiter_uuid=payload.get("waiter_uuid"),
            order_source=order_source,
            cash_register_uuid=payload.get("cash_register_uuid"),
            pickup_code=payload.get("pickup_code"),
            pickup_status=payload.get("pickup_status"),
            ready_at=ready_at,
            payment_status=str(payload.get("payment_status") or "open"),
            collective_bill_id=collective_bill_id,
            order_number=payload.get("order_number"),
            payload_json=json.dumps(payload),
            print_status="done",
        )
        db.add(row)
    else:
        row.session_id = session_id
        row.table_number = table_number
        row.waiter_uuid = payload.get("waiter_uuid")
        row.order_source = order_source
        row.cash_register_uuid = payload.get("cash_register_uuid")
        row.pickup_code = payload.get("pickup_code")
        row.pickup_status = payload.get("pickup_status")
        row.ready_at = ready_at
        row.payment_status = str(payload.get("payment_status") or "open")
        row.collective_bill_id = collective_bill_id
        if payload.get("order_number") is not None:
            row.order_number = int(payload["order_number"])
        row.payload_json = json.dumps(payload)
    db.flush()
    return row


def _ghost_cleanup_orders(db: Session, *, event_id: int, keep_client_ids: set[str]) -> int:
    purged = 0
    rows = (
        db.query(LocalOrder)
        .filter(LocalOrder.event_id == event_id, LocalOrder.payment_status == "open")
        .all()
    )
    for row in rows:
        if row.client_order_id in keep_client_ids:
            continue
        db.query(KitchenTicketLine).filter(
            KitchenTicketLine.ticket_id.in_(
                db.query(KitchenTicket.id).filter(KitchenTicket.local_order_id == row.id)
            )
        ).delete(synchronize_session=False)
        db.query(KitchenTicket).filter(KitchenTicket.local_order_id == row.id).delete(synchronize_session=False)
        db.query(OutboxEntry).filter(
            OutboxEntry.event_id == event_id,
            OutboxEntry.payload_json.contains(row.client_order_id),
        ).delete(synchronize_session=False)
        db.delete(row)
        purged += 1
    if purged:
        db.flush()
    return purged


def _restore_cash_session(db: Session, *, event_id: int, payload: dict) -> None:
    subject_key = payload.get("subject_key")
    subject_type = str(payload.get("subject_type") or "waiter").lower()
    if not subject_key:
        if subject_type == "cash_register" and payload.get("cash_register_uuid"):
            subject_key = f"cash_register:{payload['cash_register_uuid']}"
        elif payload.get("waiter_uuid"):
            subject_key = f"waiter:{payload['waiter_uuid']}"
    if not subject_key:
        return

    q = db.query(CashSession).filter(CashSession.event_id == event_id, CashSession.status == "OPEN")
    if subject_type == "cash_register":
        row = q.filter(CashSession.cash_register_uuid == payload.get("cash_register_uuid")).first()
    else:
        row = q.filter(CashSession.waiter_uuid == payload.get("waiter_uuid")).first()

    if not row:
        row = CashSession(
            event_id=event_id,
            subject_type=subject_type,
            waiter_uuid=payload.get("waiter_uuid"),
            cash_register_uuid=payload.get("cash_register_uuid"),
            subject_name=str(payload.get("subject_name") or ""),
            operator_waiter_uuid=payload.get("operator_waiter_uuid"),
            status=str(payload.get("status") or "OPEN"),
            opening_balance_cents=int(payload.get("opening_balance_cents") or 0),
            wallet_cents=int(payload.get("wallet_cents") or 0),
            total_cash_cents=int(payload.get("total_cash_cents") or 0),
            total_non_cash_cents=int(payload.get("total_non_cash_cents") or 0),
            counted_cash_cents=payload.get("counted_cash_cents"),
            variance_cents=payload.get("variance_cents"),
            started_at=_parse_dt(payload.get("started_at")),
            ended_at=_parse_dt(payload.get("ended_at")),
        )
        db.add(row)
        db.flush()
    else:
        row.subject_name = str(payload.get("subject_name") or row.subject_name)
        row.operator_waiter_uuid = payload.get("operator_waiter_uuid")
        row.status = str(payload.get("status") or row.status)
        row.opening_balance_cents = int(payload.get("opening_balance_cents") or 0)
        row.wallet_cents = int(payload.get("wallet_cents") or 0)
        row.total_cash_cents = int(payload.get("total_cash_cents") or 0)
        row.total_non_cash_cents = int(payload.get("total_non_cash_cents") or 0)
        row.counted_cash_cents = payload.get("counted_cash_cents")
        row.variance_cents = payload.get("variance_cents")
        row.started_at = _parse_dt(payload.get("started_at")) or row.started_at
        row.ended_at = _parse_dt(payload.get("ended_at"))

    db.query(CashSessionLedger).filter(CashSessionLedger.cash_session_id == row.id).delete(
        synchronize_session=False
    )
    for entry in payload.get("ledger") or []:
        if not isinstance(entry, dict):
            continue
        db.add(
            CashSessionLedger(
                cash_session_id=row.id,
                entry_type=str(entry.get("entry_type") or ""),
                amount_cents=int(entry.get("amount_cents") or 0),
                affects_wallet=1 if entry.get("affects_wallet") else 0,
                method=entry.get("method"),
                voucher_name=entry.get("voucher_name"),
                reference_id=entry.get("reference_id"),
                payload_json=json.dumps(entry),
            )
        )
    db.flush()


def _restore_kitchen_tickets(
    db: Session,
    *,
    order: LocalOrder,
    tickets: list[dict],
    ev: dict | None,
) -> int:
    restored = 0
    db.query(KitchenTicketLine).filter(
        KitchenTicketLine.ticket_id.in_(
            db.query(KitchenTicket.id).filter(KitchenTicket.local_order_id == order.id)
        )
    ).delete(synchronize_session=False)
    db.query(KitchenTicket).filter(KitchenTicket.local_order_id == order.id).delete(synchronize_session=False)
    db.flush()

    if tickets:
        for t in tickets:
            if not isinstance(t, dict):
                continue
            ticket = KitchenTicket(
                local_order_id=order.id,
                order_submission_id=order.id,
                event_id=order.event_id,
                station_uuid=str(t.get("station_uuid") or ""),
                printer_appliance_id=t.get("printer_appliance_id"),
                status=str(t.get("status") or "open"),
            )
            db.add(ticket)
            db.flush()
            for line in t.get("lines") or []:
                if not isinstance(line, dict):
                    continue
                line_payload = line.get("line_payload") or {}
                db.add(
                    KitchenTicketLine(
                        ticket_id=ticket.id,
                        line_index=int(line.get("line_index") or 0),
                        line_payload_json=json.dumps(line_payload),
                        qty_total=int(line.get("qty_total") or 1),
                        qty_printed=int(line.get("qty_printed") or 0),
                    )
                )
            restored += 1
        return restored

    if not ev:
        return 0
    payload = json.loads(order.payload_json or "{}")
    lines = payload.get("lines") or []
    if not lines:
        return 0
    order_ctx = {
        "table_number": payload.get("table_number"),
        "pickup_code": payload.get("pickup_code"),
    }
    groups = group_lines_by_station(ev, lines)
    for station_uuid, station_lines in groups.items():
        if not station_lines or station_uuid is None:
            continue
        for printer_id, printer_lines in subgroup_lines_by_printer(ev, station_uuid, station_lines, order_ctx).items():
            if not printer_lines or not printer_in_kitchen_monitor(ev, printer_id):
                continue
            ticket = KitchenTicket(
                local_order_id=order.id,
                order_submission_id=order.id,
                event_id=order.event_id,
                station_uuid=str(station_uuid),
                printer_appliance_id=printer_id,
                status="open",
            )
            db.add(ticket)
            db.flush()
            for idx, line in enumerate(printer_lines):
                if not isinstance(line, dict):
                    continue
                qty = max(1, int(line.get("qty") or 1))
                db.add(
                    KitchenTicketLine(
                        ticket_id=ticket.id,
                        line_index=idx,
                        line_payload_json=json.dumps(dict(line)),
                        qty_total=qty,
                        qty_printed=0,
                    )
                )
            restored += 1
    return restored


def _bump_counters(db: Session, *, event_id: int, payloads: list[dict]) -> None:
    max_order = 0
    max_pickup = 0
    for payload in payloads:
        on = payload.get("order_number")
        if on is not None:
            max_order = max(max_order, int(on))
        pn = payload.get("pickup_number")
        if pn is not None:
            max_pickup = max(max_pickup, int(pn))
    if max_order:
        row = db.query(EventOrderCounter).filter(EventOrderCounter.event_id == event_id).first()
        next_num = max_order + 1
        if not row:
            db.add(EventOrderCounter(event_id=event_id, next_number=next_num))
        elif int(row.next_number or 1) <= max_order:
            row.next_number = next_num
    if max_pickup:
        row = db.query(EventPickupCounter).filter(EventPickupCounter.event_id == event_id).first()
        next_num = max_pickup + 1
        if not row:
            db.add(EventPickupCounter(event_id=event_id, next_number=next_num))
        elif int(row.next_number or 1) <= max_pickup:
            row.next_number = next_num


def _apply_stock_for_open_orders(db: Session, bundle: dict, event_id: int, payloads: list[dict]) -> None:
    data = json.loads(json.dumps(bundle))
    for payload in payloads:
        lines = payload.get("lines") or []
        if lines:
            apply_stock_to_bundle(data, event_id, lines)
    save_bundle(db, data)


def restore_operational_snapshot(db: Session, snapshot: dict, bundle: dict | None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "restored_orders": 0,
        "restored_kitchen_tickets": 0,
        "restored_cash_sessions": 0,
        "purged_ghost_orders": 0,
        "events": [],
    }
    kitchen_by_cid: dict[str, list[dict]] = {}
    for event_snap in snapshot.get("events") or []:
        event_id = int(event_snap.get("event_id") or 0)
        if not event_id:
            continue
        for entry in event_snap.get("kitchen_tickets") or []:
            cid = str(entry.get("client_order_id") or "")
            if cid:
                kitchen_by_cid[cid] = entry.get("tickets") or []

        bill_by_uuid: dict[str, PaymentBatch] = {}
        for bill in event_snap.get("collective_bills") or []:
            row = _upsert_collective_bill(db, event_id=event_id, bill=bill)
            if row:
                bill_by_uuid[row.uuid] = row

        keep_cids: set[str] = set()
        payloads: list[dict] = []
        for entry in event_snap.get("open_orders") or []:
            cid = str(entry.get("client_order_id") or "")
            payload = entry.get("payload") or {}
            if not cid:
                continue
            payload = {**payload, "client_order_id": cid}
            order = _restore_order(
                db,
                event_id=event_id,
                client_order_id=cid,
                payload=payload,
                bill_by_uuid=bill_by_uuid,
            )
            keep_cids.add(cid)
            payloads.append(payload)
            summary["restored_orders"] += 1
            ev = event_from_bundle(bundle, event_id)
            summary["restored_kitchen_tickets"] += _restore_kitchen_tickets(
                db,
                order=order,
                tickets=kitchen_by_cid.get(cid) or [],
                ev=ev,
            )

        summary["purged_ghost_orders"] += _ghost_cleanup_orders(db, event_id=event_id, keep_client_ids=keep_cids)

        for entry in event_snap.get("open_cash_sessions") or []:
            payload = entry.get("payload") or {}
            if entry.get("subject_key"):
                payload = {**payload, "subject_key": entry["subject_key"]}
            _restore_cash_session(db, event_id=event_id, payload=payload)
            summary["restored_cash_sessions"] += 1

        _bump_counters(db, event_id=event_id, payloads=payloads)
        if bundle and payloads:
            _apply_stock_for_open_orders(db, bundle, event_id, payloads)

        summary["events"].append(event_id)

    db.commit()
    return summary
