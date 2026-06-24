"""Kitchen monitor and pickup order routes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..domain.kitchen_sync import enqueue_kitchen_tickets_sync
from ..models import KitchenTicket, KitchenTicketLine, LocalOrder
from ..print_worker import station_name_from_event
from ..printer_routing import (
    kitchen_monitor_label,
    kitchen_monitors_enabled,
    kitchen_monitors_for_event,
    printer_in_kitchen_monitor,
)
from ..schemas.edge import (
    KitchenOrdersResponse,
    KitchenPrintersResponse,
    KitchenStationsResponse,
    KitchenTicketPrintResponse,
    PickupOrdersResponse,
    PickupPickedUpResponse,
)
from .edge_common import (
    _article_map,
    _create_print_job_for_lines,
    _set_pickup_ready_if_complete,
    _station_config_for_uuid,
    _sync_outbox_payload,
)

router = APIRouter()


def _kitchen_printers_for_event(ev: dict) -> list[dict]:
    if not kitchen_monitors_enabled(ev):
        return []
    return kitchen_monitors_for_event(ev)


def _kitchen_line_response(row: KitchenTicketLine, articles: dict) -> dict:
    line = json.loads(row.line_payload_json)
    aid = line.get("article_id")
    art = articles.get(str(aid)) or articles.get(aid) or {}
    if aid is not None and not line.get("article_name"):
        line["article_name"] = art.get("name") or f"#{aid}"
    remaining = max(0, int(row.qty_total or 0) - int(row.qty_printed or 0))
    return {
        "id": row.id,
        "line_index": row.line_index,
        "line": line,
        "qty_total": int(row.qty_total or 0),
        "qty_printed": int(row.qty_printed or 0),
        "qty_remaining": remaining,
    }


def _serialize_kitchen_ticket(
    ticket: KitchenTicket,
    order: LocalOrder,
    lines: list[KitchenTicketLine],
    ev: dict,
) -> dict:
    payload = json.loads(order.payload_json)
    arts = _article_map(ev)
    line_rows = [_kitchen_line_response(row, arts) for row in sorted(lines, key=lambda r: (r.line_index, r.id))]
    line_rows = [row for row in line_rows if row["qty_remaining"] > 0]
    return {
        "id": ticket.id,
        "local_order_id": ticket.local_order_id,
        "event_id": ticket.event_id,
        "station_uuid": ticket.station_uuid,
        "station_name": station_name_from_event(ev, ticket.station_uuid),
        "printer_appliance_id": ticket.printer_appliance_id,
        "printer_label": kitchen_monitor_label(ev, ticket.printer_appliance_id),
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "client_order_id": order.client_order_id,
        "table_number": payload.get("table_number"),
        "pickup_code": payload.get("pickup_code"),
        "order_source": payload.get("order_source") or "waiter",
        "waiter_uuid": payload.get("waiter_uuid"),
        "waiter_name": payload.get("waiter_name"),
        "order_number": payload.get("order_number"),
        "ordered_at": payload.get("ordered_at"),
        "lines": line_rows,
    }


def _update_kitchen_ticket_status(db: Session, ticket: KitchenTicket) -> None:
    lines = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).all()
    remaining = sum(max(0, int(ln.qty_total or 0) - int(ln.qty_printed or 0)) for ln in lines)
    printed = sum(int(ln.qty_printed or 0) for ln in lines)
    if remaining <= 0:
        ticket.status = "done"
    elif printed > 0:
        ticket.status = "partial"
    else:
        ticket.status = "open"


def _enqueue_kitchen_ticket_print(
    db: Session,
    *,
    ticket: KitchenTicket,
    selected_lines: list[tuple[KitchenTicketLine, int]],
) -> int:
    order = db.query(LocalOrder).filter(LocalOrder.id == ticket.local_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, ticket.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    if not kitchen_monitors_enabled(ev):
        raise HTTPException(status_code=400, detail="Kitchen monitor is not active for this event")
    if ticket.printer_appliance_id is not None and not printer_in_kitchen_monitor(ev, ticket.printer_appliance_id):
        raise HTTPException(status_code=400, detail="Kitchen monitor is not active for this printer")

    payload = json.loads(order.payload_json)
    printable_lines: list[dict] = []
    for line_row, qty in selected_lines:
        remaining = max(0, int(line_row.qty_total or 0) - int(line_row.qty_printed or 0))
        qty = int(qty)
        if qty < 1 or qty > remaining:
            raise HTTPException(status_code=400, detail="Requested quantity exceeds remaining quantity")
        line = json.loads(line_row.line_payload_json)
        line["qty"] = qty
        printable_lines.append(line)

    if not printable_lines:
        raise HTTPException(status_code=400, detail="Nothing left to print")

    job_id = _create_print_job_for_lines(
        db,
        order_id=order.id,
        station_uuid=ticket.station_uuid,
        payload=payload,
        station_lines=printable_lines,
        ev=ev,
        articles=_article_map(ev),
        job_kind="kitchen_ticket",
        printer_appliance_id=ticket.printer_appliance_id,
        table_number=payload.get("table_number"),
        pickup_code=payload.get("pickup_code"),
    )
    for line_row, qty in selected_lines:
        line_row.qty_printed = int(line_row.qty_printed or 0) + int(qty)
    _update_kitchen_ticket_status(db, ticket)
    db.flush()
    _set_pickup_ready_if_complete(db, order)
    enqueue_kitchen_tickets_sync(db, order)
    db.commit()
    return job_id


@router.get("/v1/kitchen/printers", response_model=KitchenPrintersResponse)
def list_kitchen_printers(event_id: int = Query(...), db: Session = Depends(get_db)) -> KitchenPrintersResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    printers = [
        {
            "printer_appliance_id": int(row["printer_appliance_id"]),
            "label": str(row.get("label") or f"Drucker #{row['printer_appliance_id']}"),
            "sort_order": int(row.get("sort_order") or 0),
        }
        for row in _kitchen_printers_for_event(ev)
    ]
    return KitchenPrintersResponse(printers=printers)


@router.get("/v1/kitchen/stations", response_model=KitchenStationsResponse)
def list_kitchen_stations(event_id: int = Query(...), db: Session = Depends(get_db)) -> KitchenStationsResponse:
    """Legacy alias: returns printer tabs as pseudo-stations for older clients."""
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    stations = [
        {
            "uuid": str(row["printer_appliance_id"]),
            "name": str(row.get("label") or f"Drucker #{row['printer_appliance_id']}"),
            "sort_order": int(row.get("sort_order") or 0),
        }
        for row in _kitchen_printers_for_event(ev)
    ]
    return KitchenStationsResponse(stations=stations)


@router.get("/v1/kitchen/orders", response_model=KitchenOrdersResponse)
def list_kitchen_orders(
    event_id: int = Query(...),
    station_uuid: str | None = Query(None),
    printer_appliance_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> KitchenOrdersResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    if not kitchen_monitors_enabled(ev):
        raise HTTPException(status_code=400, detail="Kitchen monitor is not active for this event")

    target_printer_id = printer_appliance_id
    if target_printer_id is None and station_uuid is not None:
        try:
            target_printer_id = int(station_uuid)
        except (TypeError, ValueError):
            st = _station_config_for_uuid(ev, station_uuid)
            if st and st.get("printer_appliance_id") is not None:
                target_printer_id = int(st["printer_appliance_id"])
    if target_printer_id is None:
        raise HTTPException(status_code=400, detail="printer_appliance_id is required")
    if not printer_in_kitchen_monitor(ev, target_printer_id):
        raise HTTPException(status_code=400, detail="Kitchen monitor is not active for this printer")

    tickets = (
        db.query(KitchenTicket)
        .filter(
            KitchenTicket.event_id == event_id,
            KitchenTicket.printer_appliance_id == int(target_printer_id),
            KitchenTicket.status != "done",
        )
        .order_by(KitchenTicket.id.asc())
        .all()
    )
    out = []
    for ticket in tickets:
        order = db.query(LocalOrder).filter(LocalOrder.id == ticket.local_order_id).first()
        if not order:
            continue
        lines = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).all()
        serialized = _serialize_kitchen_ticket(ticket, order, lines, ev)
        if serialized["lines"]:
            out.append(serialized)
    return KitchenOrdersResponse(orders=out)


@router.post("/v1/kitchen/tickets/{ticket_id}/print", response_model=KitchenTicketPrintResponse)
def print_kitchen_ticket(ticket_id: int, db: Session = Depends(get_db)) -> KitchenTicketPrintResponse:
    ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found")
    if ticket.status == "done":
        raise HTTPException(status_code=400, detail="Kitchen ticket is already done")
    lines = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).all()
    selected = [
        (ln, max(0, int(ln.qty_total or 0) - int(ln.qty_printed or 0)))
        for ln in lines
        if max(0, int(ln.qty_total or 0) - int(ln.qty_printed or 0)) > 0
    ]
    job_id = _enqueue_kitchen_ticket_print(db, ticket=ticket, selected_lines=selected)
    return KitchenTicketPrintResponse(print_job_id=job_id, ticket_status=ticket.status)


@router.post("/v1/kitchen/tickets/{ticket_id}/lines/{line_id}/print-one", response_model=KitchenTicketPrintResponse)
def print_kitchen_ticket_line_unit(ticket_id: int, line_id: int, db: Session = Depends(get_db)) -> KitchenTicketPrintResponse:
    ticket = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found")
    if ticket.status == "done":
        raise HTTPException(status_code=400, detail="Kitchen ticket is already done")
    line = (
        db.query(KitchenTicketLine)
        .filter(KitchenTicketLine.id == line_id, KitchenTicketLine.ticket_id == ticket.id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Kitchen ticket line not found")
    job_id = _enqueue_kitchen_ticket_print(db, ticket=ticket, selected_lines=[(line, 1)])
    return KitchenTicketPrintResponse(print_job_id=job_id, ticket_status=ticket.status)


def _pickup_order_response(order: LocalOrder) -> dict[str, Any]:
    payload = json.loads(order.payload_json)
    return {
        "local_order_id": order.id,
        "client_order_id": order.client_order_id,
        "pickup_code": order.pickup_code or payload.get("pickup_code"),
        "pickup_status": order.pickup_status or payload.get("pickup_status") or "pending",
        "cash_register_uuid": order.cash_register_uuid or payload.get("cash_register_uuid"),
        "cash_register_name": payload.get("cash_register_name"),
        "order_number": payload.get("order_number"),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "ready_at": order.ready_at.isoformat() if order.ready_at else payload.get("ready_at"),
        "item_count": sum(max(1, int(line.get("qty") or 1)) for line in payload.get("lines") or [] if isinstance(line, dict)),
    }


READY_PICKUP_TTL = timedelta(minutes=5)


def _mark_pickup_order_picked_up(db: Session, order: LocalOrder) -> None:
    order.pickup_status = "picked_up"
    order.picked_up_at = datetime.now(timezone.utc)
    payload = json.loads(order.payload_json)
    payload["pickup_status"] = "picked_up"
    payload["picked_up_at"] = order.picked_up_at.isoformat()
    order.payload_json = json.dumps(payload)
    _sync_outbox_payload(db, order, payload)


def _expire_stale_ready_pickup_orders(db: Session, event_id: int) -> None:
    cutoff = datetime.now(timezone.utc) - READY_PICKUP_TTL
    stale = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.order_source == "cash_register",
            LocalOrder.pickup_status == "ready",
            LocalOrder.ready_at.isnot(None),
            LocalOrder.ready_at < cutoff,
        )
        .all()
    )
    for order in stale:
        _mark_pickup_order_picked_up(db, order)


@router.get("/v1/pickup/orders", response_model=PickupOrdersResponse)
def list_pickup_orders(event_id: int = Query(...), db: Session = Depends(get_db)) -> PickupOrdersResponse:
    _expire_stale_ready_pickup_orders(db, event_id)
    db.commit()
    rows = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.order_source == "cash_register",
            LocalOrder.pickup_status.in_(["pending", "ready"]),
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    pending = [row for row in rows if row.pickup_status != "ready"]
    ready = sorted(
        (row for row in rows if row.pickup_status == "ready"),
        key=lambda row: row.ready_at or datetime.min.replace(tzinfo=timezone.utc),
    )
    return PickupOrdersResponse(orders=[_pickup_order_response(row) for row in pending + ready])


@router.post("/v1/pickup/orders/{order_id}/picked-up", response_model=PickupPickedUpResponse)
def mark_pickup_order_picked_up(order_id: int, db: Session = Depends(get_db)) -> PickupPickedUpResponse:
    order = db.query(LocalOrder).filter(LocalOrder.id == order_id).first()
    if not order or order.order_source != "cash_register":
        raise HTTPException(status_code=404, detail="Pickup order not found")
    _mark_pickup_order_picked_up(db, order)
    db.commit()
    return PickupPickedUpResponse(local_order_id=order.id, pickup_status="picked_up")
