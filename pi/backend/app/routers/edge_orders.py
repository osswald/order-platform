"""Order creation, payment, tables, and collective bill routes."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..bundle_cache import event_from_bundle, get_bundle_dict
from ..deps import get_db
from ..discounts import validate_submit_discounts
from ..domain.items import upsert_items_from_payload
from ..domain.kitchen_sync import enqueue_kitchen_tickets_sync
from ..domain.sessions import ensure_order_session
from ..domain.sync_enqueue import enqueue_payload_sync, enrich_payload_for_cloud_sync, event_mode_label
from ..instant_collective_bill import ensure_instant_collective_bill
from ..line_moves import append_lines_to_collective, append_lines_to_table, take_from_orders
from ..models import CollectiveBill, LocalOrder
from ..order_fiscal import (
    allocate_order_number,
    distinct_order_numbers_for_local_orders,
    distinct_order_numbers_from_payload,
    is_ferdig_client_order_id,
    snapshot_lines,
    waiter_name_from_event,
)
from ..order_line_utils import copy_line_fiscal_fields
from ..order_line_utils import line_key as _line_key
from ..position_comments import validate_submit_position_notes
from ..pricing import normalize_discount, order_lines_gross_cents, order_total_cents
from ..print_worker import group_lines_by_station
from ..printer_routing import printer_in_kitchen_monitor, subgroup_lines_by_printer
from ..schemas.edge import (
    AccountSummaryResponse,
    AssignCollectiveBody,
    AssignCollectiveResponse,
    CollectiveBillCreateBody,
    CollectiveBillCreatedResponse,
    CollectivePartialSettleResponse,
    CollectiveSettleResponse,
    LineSelection,
    LocalOrderCreate,
    LocalOrderCreatedResponse,
    OpenCollectiveBillsResponse,
    OpenTablesResponse,
    OrderPayBody,
    OrderPayResponse,
    TablePartialSettleResponse,
    TableSettleBody,
    TableSettlePartialBody,
    TableSettleResponse,
    TransferLinesBody,
    TransferLinesResponse,
)
from ..schemas.order_models import dump_discount, dump_lines, dump_payments
from ..stock import apply_stock_to_bundle, save_bundle, validate_stock
from ..vouchers import (
    article_lines_only,
    compute_voucher_credits,
    is_voucher_sale_line,
    order_lines_total_cents,
    voucher_definition_by_uuid,
    voucher_sale_unit_cents,
)
from .edge_common import (
    PAYMENT_MODES_CASH,
    _allocate_pickup_number,
    _article_map,
    _build_line_groups_from_orders,
    _cash_register_from_event,
    _collective_bill_open,
    _create_customer_pickup_print_job_for_lines,
    _create_kitchen_ticket,
    _create_payment_receipt,
    _create_print_job_for_lines,
    _create_voucher_print_job,
    _line_totals,
    _lines_with_station_uuid,
    _normalize_additions,
    _payment_status_for_create,
    _payments_total_cents,
    _receipt_payload_from_orders,
    _selections_total_cents_from_groups,
    _set_pickup_ready_if_complete,
    _summary_from_orders,
    _sync_outbox_payload,
    _validate_payment_types,
)

router = APIRouter()


@router.post("/v1/orders", response_model=LocalOrderCreatedResponse)
def create_local_order(body: LocalOrderCreate, db: Session = Depends(get_db)) -> LocalOrderCreatedResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    lines = dump_lines(body.lines)
    payments = dump_payments(body.payments)
    order_discount_raw = dump_discount(body.order_discount)

    if db.query(LocalOrder).filter(LocalOrder.client_order_id == body.client_order_id).first():
        raise HTTPException(status_code=409, detail="Duplicate client_order_id")

    line_dicts = [
        {
            "article_id": ln.get("article_id"),
            "qty": ln.get("qty"),
            "note": ln.get("note") or "",
            "additions": ln.get("additions") or [],
        }
        for ln in lines
        if isinstance(ln, dict) and ln.get("article_id") is not None and not is_voucher_sale_line(ln)
    ]
    validate_stock(ev, line_dicts)
    has_voucher_sale = any(is_voucher_sale_line(ln) for ln in lines if isinstance(ln, dict))

    order_source = (body.order_source or "waiter").strip().lower()
    if order_source not in {"waiter", "cash_register"}:
        raise HTTPException(status_code=400, detail="Unsupported order_source")
    if body.cash_register_uuid:
        order_source = "cash_register"

    reg = _cash_register_from_event(ev, body.cash_register_uuid)
    if order_source == "cash_register" and not reg:
        raise HTTPException(status_code=400, detail="Unknown cash register for this event")
    if order_source != "cash_register" and body.table_number is None:
        raise HTTPException(status_code=400, detail="table_number is required for waiter orders")

    pm = (ev.get("payment_mode") or "pay_later").lower()
    arts = _article_map(ev)
    _validate_payment_types(ev, payments)
    normalized_order_discount = validate_submit_discounts(ev, lines, order_discount_raw, arts)
    validate_submit_position_notes(bundle, lines)
    line_cents, _ = order_lines_total_cents(lines, ev, arts, normalized_order_discount)
    redemptions_in = [r.model_dump() for r in body.voucher_redemptions]
    if redemptions_in and not payments:
        raise HTTPException(status_code=400, detail="Gutschein einlösen erfordert Zahlung")
    article_gross = order_lines_gross_cents(article_lines_only(lines), ev, arts)
    voucher_credit = 0
    voucher_records: list[dict] = []
    if redemptions_in:
        voucher_credit, voucher_records = compute_voucher_credits(
            ev,
            gross_cents=article_gross,
            redemptions=redemptions_in,
            articles=arts,
        )
    expected_cents = max(0, line_cents - voucher_credit)
    instant_bill = None
    if order_source == "cash_register":
        if not payments:
            raise HTTPException(status_code=400, detail="payments required for cash-register orders")
        if _payments_total_cents(payments) != expected_cents:
            raise HTTPException(status_code=400, detail="payment amount must match order total")
    elif pm == "instant":
        payments = []
        instant_bill = ensure_instant_collective_bill(db, ev)
        if not instant_bill:
            raise HTTPException(status_code=400, detail="Sammelrechnung für Sofort-Zahlung nicht konfiguriert")

    payment_status = "paid" if order_source == "cash_register" else _payment_status_for_create(ev, payments)
    if has_voucher_sale and payment_status != "paid":
        raise HTTPException(status_code=400, detail="Gutscheinverkauf erfordert Zahlung")
    order_lines = _lines_with_station_uuid(ev, lines)
    article_order_lines = article_lines_only(order_lines)
    table_number_payload = None if order_source == "cash_register" else body.table_number
    table_number_db = 0 if order_source == "cash_register" else body.table_number
    pickup_number: int | None = None
    pickup_code: str | None = None
    pickup_status: str | None = None
    if order_source == "cash_register":
        pickup_number = _allocate_pickup_number(db, body.event_id)
        prefix = str(reg.get("pickup_code_prefix") or "").strip().upper()
        pickup_code = f"{prefix}{pickup_number}"
        pickup_status = "pending"
    payload: dict = {
        "client_order_id": body.client_order_id,
        "event_id": body.event_id,
        "table_number": table_number_payload,
        "waiter_uuid": body.waiter_uuid,
        "lines": order_lines,
        "payments": payments,
        "payment_status": payment_status,
        "order_source": order_source,
        "mode": event_mode_label(str(ev.get("status"))),
    }
    if voucher_records:
        payload["voucher_redemptions"] = voucher_records
        payload["voucher_credit_cents"] = voucher_credit
    if normalized_order_discount:
        payload["order_discount"] = normalized_order_discount
    if instant_bill:
        payload["collective_bill_uuid"] = instant_bill.uuid
        payload["collective_bill_name"] = instant_bill.name
    if order_source == "cash_register":
        payload.update(
            {
                "cash_register_uuid": body.cash_register_uuid,
                "cash_register_name": reg.get("name"),
                "pickup_prefix": reg.get("pickup_code_prefix"),
                "pickup_number": pickup_number,
                "pickup_code": pickup_code,
                "pickup_status": pickup_status,
            }
        )
    order_number: int | None = None
    if is_ferdig_client_order_id(body.client_order_id):
        order_number = allocate_order_number(db, body.event_id)
        ordered_at = datetime.now(UTC).isoformat()
        waiter_name = waiter_name_from_event(ev, body.waiter_uuid)
        order_lines = snapshot_lines(order_lines, arts, order_number=order_number, event=ev)
        payload["order_number"] = order_number
        payload["ordered_at"] = ordered_at
        payload["lines"] = order_lines
        if waiter_name:
            payload["waiter_name"] = waiter_name
    session_id = ensure_order_session(
        db,
        event_id=body.event_id,
        table_number=table_number_db if table_number_db else None,
        waiter_uuid=body.waiter_uuid,
        order_source=order_source,
        cash_register_uuid=body.cash_register_uuid if order_source == "cash_register" else None,
        pickup_code=pickup_code,
    )
    order = LocalOrder(
        session_id=session_id,
        client_order_id=body.client_order_id,
        event_id=body.event_id,
        table_number=table_number_db,
        waiter_uuid=body.waiter_uuid,
        order_source=order_source,
        cash_register_uuid=body.cash_register_uuid if order_source == "cash_register" else None,
        pickup_code=pickup_code,
        pickup_status=pickup_status,
        payment_status=payment_status,
        collective_bill_id=instant_bill.id if instant_bill else None,
        payload_json=json.dumps(payload),
        print_status="pending",
    )
    db.add(order)
    db.flush()
    upsert_items_from_payload(
        db,
        session_id=session_id,
        submission_id=order.id,
        event_id=body.event_id,
        table_number=table_number_db if table_number_db else None,
        collective_batch_id=None,
        lines=order_lines,
        order_number=order_number,
        ordered_at=datetime.now(UTC) if order_number else None,
    )

    groups = group_lines_by_station(ev, article_order_lines)
    print_job_ids: list[int] = []
    customer_print_job_ids: list[int] = []
    kitchen_ticket_ids: list[int] = []

    if payment_status == "paid" and has_voucher_sale:
        slip_units: list[tuple[str, int]] = []
        for line in order_lines:
            if not is_voucher_sale_line(line):
                continue
            vd = voucher_definition_by_uuid(ev, str(line.get("voucher_definition_uuid") or ""))
            name = (vd or {}).get("name") or "Gutschein"
            uc = voucher_sale_unit_cents(ev, line)
            qty = max(1, int(line.get("qty") or 1))
            slip_units.extend([(name, uc)] * qty)
        total_slips = len(slip_units)
        for idx, (vname, uc) in enumerate(slip_units, start=1):
            print_job_ids.append(
                _create_voucher_print_job(
                    db,
                    order_id=order.id,
                    ev=ev,
                    cash_register_uuid=body.cash_register_uuid,
                    voucher_name=vname,
                    value_cents=uc,
                    copy_index=idx if total_slips > 1 else None,
                    copy_total=total_slips if total_slips > 1 else None,
                )
            )

    for station_uuid, station_lines in groups.items():
        if not station_lines:
            continue
        order_ctx = {
            "table_number": payload.get("table_number"),
            "pickup_code": payload.get("pickup_code"),
        }
        printer_groups = subgroup_lines_by_printer(ev, station_uuid, station_lines, order_ctx)
        for printer_id, printer_lines in printer_groups.items():
            if not printer_lines:
                continue
            if printer_in_kitchen_monitor(ev, printer_id) and station_uuid is not None:
                kitchen_ticket_ids.append(
                    _create_kitchen_ticket(
                        db,
                        order_id=order.id,
                        event_id=body.event_id,
                        station_uuid=str(station_uuid),
                        station_lines=printer_lines,
                        printer_appliance_id=printer_id,
                    )
                )
            else:
                print_job_ids.append(
                    _create_print_job_for_lines(
                        db,
                        order_id=order.id,
                        station_uuid=station_uuid,
                        payload=payload,
                        station_lines=printer_lines,
                        ev=ev,
                        articles=arts,
                        printer_appliance_id=printer_id,
                        table_number=payload.get("table_number"),
                        pickup_code=payload.get("pickup_code"),
                    )
                )
        if order_source == "cash_register":
            customer_print_job_ids.append(
                _create_customer_pickup_print_job_for_lines(
                    db,
                    order_id=order.id,
                    cash_register_uuid=str(body.cash_register_uuid),
                    station_uuid=station_uuid,
                    payload=payload,
                    station_lines=station_lines,
                    ev=ev,
                    articles=arts,
                )
            )

    if order_source == "cash_register" and not kitchen_ticket_ids:
        _set_pickup_ready_if_complete(db, order)
        payload = json.loads(order.payload_json)

    if kitchen_ticket_ids:
        enqueue_kitchen_tickets_sync(db, order)

    enqueue_payload_sync(
        db,
        event_id=body.event_id,
        client_order_id=body.client_order_id,
        payload=enrich_payload_for_cloud_sync(
            payload,
            local_order_id=order.id,
            session_id=session_id,
            mode=event_mode_label(str(ev.get("status"))),
        ),
    )

    from ..shift_integration import record_shift_order_submit

    order_amount = order_total_cents(order_lines, normalized_order_discount, ev, arts)
    record_shift_order_submit(
        db,
        ev,
        event_id=body.event_id,
        waiter_uuid=body.waiter_uuid,
        cash_register_uuid=body.cash_register_uuid if order_source == "cash_register" else None,
        amount_cents=order_amount,
        reference_id=body.client_order_id,
        voucher_records=voucher_records if voucher_records and payment_status != "paid" else None,
    )

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")
    validate_stock(ev, line_dicts)
    stock_patch = apply_stock_to_bundle(bundle, body.event_id, line_dicts, strict=True)
    save_bundle(db, bundle)

    payment_receipt_id = None
    if payment_status == "paid" and payments:
        payment_receipt_id = _create_payment_receipt(
            db,
            ev,
            payload,
            source_type="order",
            source_id=order.id,
        ).id

    db.commit()
    return LocalOrderCreatedResponse(
        local_order_id=order.id,
        payment_id=payment_receipt_id,
        order_number=order_number,
        print_job_id=print_job_ids[0] if print_job_ids else None,
        print_job_ids=print_job_ids,
        customer_print_job_ids=customer_print_job_ids,
        kitchen_ticket_ids=kitchen_ticket_ids,
        payment_status=payment_status,
        pickup_code=pickup_code,
        pickup_status=payload.get("pickup_status") if order_source == "cash_register" else None,
        payment_mode=(ev.get("payment_mode") or "pay_later").lower(),
        articles=stock_patch.get("articles") or {},
        ingredients=stock_patch.get("ingredients") or {},
    )


@router.post("/v1/orders/{order_id}/pay", response_model=OrderPayResponse)
def pay_local_order(order_id: int, body: OrderPayBody, db: Session = Depends(get_db)) -> OrderPayResponse:
    order = db.query(LocalOrder).filter(LocalOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, order.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    pm = (ev.get("payment_mode") or "pay_later").lower()
    if pm not in PAYMENT_MODES_CASH:
        raise HTTPException(status_code=400, detail="Event does not require immediate payment")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")

    payments = dump_payments(body.payments)
    _validate_payment_types(ev, payments)

    payload = json.loads(order.payload_json)
    payload["payments"] = payments
    payload["payment_status"] = "paid"
    payload["paid_at"] = datetime.now(UTC).isoformat()
    order.payment_status = "paid"
    order.payload_json = json.dumps(payload)
    _sync_outbox_payload(db, order, payload)
    receipt = _create_payment_receipt(db, ev, payload, source_type="order", source_id=order.id)
    db.commit()
    return OrderPayResponse(local_order_id=order.id, payment_id=receipt.id, payment_status="paid")


@router.get("/v1/tables/open", response_model=OpenTablesResponse)
def list_open_tables(event_id: int = Query(...), db: Session = Depends(get_db)) -> OpenTablesResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    arts = _article_map(ev)
    currency = ev.get("currency", "EUR")
    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.payment_status == "open",
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.table_number > 0,
        )
        .order_by(LocalOrder.table_number.asc(), LocalOrder.id.asc())
        .all()
    )

    by_table: dict[int, dict] = {}
    table_order_sets: dict[int, set] = {}
    for o in orders:
        tn = int(o.table_number)
        if tn not in by_table:
            by_table[tn] = {"table_number": tn, "order_count": 0, "total_cents": 0, "item_count": 0}
            table_order_sets[tn] = set()
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        line_cents, line_qty = _line_totals(lines, arts)
        table_order_sets[tn] |= distinct_order_numbers_from_payload(payload, legacy_key=f"legacy:{o.id}")
        by_table[tn]["total_cents"] += line_cents
        by_table[tn]["item_count"] += line_qty

    for tn, row in by_table.items():
        row["order_count"] = len(table_order_sets.get(tn, set()))

    tables = [
        {**row, "currency": currency}
        for row in sorted(by_table.values(), key=lambda r: r["table_number"])
    ]
    return OpenTablesResponse(event_id=event_id, currency=currency, tables=tables)


@router.get("/v1/tables/{table_number}", response_model=AccountSummaryResponse)
def get_table_summary(
    table_number: int,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> AccountSummaryResponse:
    if table_number < 1 or table_number > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    arts = _article_map(ev)
    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )

    summary = _summary_from_orders(
        orders,
        ev,
        arts,
        {"table_number": table_number, "event_id": event_id},
    )
    aggregated_lines = []
    for o in orders:
        payload = json.loads(o.payload_json)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            aggregated_lines.append(
                {
                    "local_order_id": o.id,
                    "article_id": line.get("article_id"),
                    "qty": line.get("qty", 1),
                    "note": line.get("note", ""),
                    "additions": _normalize_additions(line.get("additions")),
                }
            )
    summary["aggregated_lines"] = aggregated_lines
    return AccountSummaryResponse.model_validate(summary)


@router.post("/v1/tables/{table_number}/settle-partial", response_model=TablePartialSettleResponse)
def settle_table_partial(
    table_number: int, body: TableSettlePartialBody, db: Session = Depends(get_db)
) -> TablePartialSettleResponse:
    if table_number < 1 or table_number > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")

    payments = dump_payments(body.payments)
    _validate_payment_types(ev, payments)

    arts = _article_map(ev)
    selections = [s.model_dump() for s in body.selections]

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    line_groups = _build_line_groups_from_orders(orders, arts)
    gross_cents = _selections_total_cents_from_groups(selections, line_groups)
    redemptions_in = [r.model_dump() for r in body.voucher_redemptions]
    voucher_credit, voucher_records = compute_voucher_credits(
        ev,
        gross_cents=gross_cents,
        redemptions=redemptions_in,
        articles=arts,
        selections=selections,
        line_groups=line_groups,
    )
    expected_cents = max(0, gross_cents - voucher_credit)
    paid_total = sum(int(p.get("amount_cents") or 0) for p in payments)
    if paid_total != expected_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match payable {expected_cents}",
        )

    need: dict[tuple, int] = {}
    for s in selections:
        key = _line_key(
            s["article_id"],
            s.get("note", ""),
            s.get("additions"),
            s.get("discount"),
        )
        need[key] = need.get(key, 0) + int(s["qty"])

    paid_lines: list[dict] = []
    order_discounts_collected: list[dict] = []
    now = datetime.now(UTC).isoformat()

    for order in orders:
        payload = json.loads(order.payload_json)
        open_lines: list[dict] = []
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            if is_voucher_sale_line(line):
                continue
            aid = line.get("article_id")
            if aid is None:
                continue
            note = str(line.get("note") or "")
            adds = _normalize_additions(line.get("additions"))
            key = _line_key(aid, note, adds, line.get("discount"))
            qty = max(1, int(line.get("qty") or 1))
            take = min(qty, need.get(key, 0))
            if take > 0:
                pl = {
                    "article_id": int(aid),
                    "qty": take,
                    "note": note,
                    "additions": adds,
                }
                su = line.get("station_uuid")
                if su:
                    pl["station_uuid"] = su
                copy_line_fiscal_fields(line, pl)
                paid_lines.append(pl)
                need[key] = need.get(key, 0) - take
                qty -= take
            if qty > 0:
                rem = {**line, "qty": qty, "additions": adds}
                open_lines.append(rem)
        payload["lines"] = open_lines
        if open_lines:
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)
        else:
            order.payment_status = "paid"
            payload["payment_status"] = "paid"
            payload["settled_at"] = now
            payload["settlement_table"] = table_number
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)
            od = normalize_discount(payload.get("order_discount"))
            if od:
                order_discounts_collected.append(od)

    leftover = sum(v for v in need.values() if v > 0)
    if leftover > 0:
        raise HTTPException(status_code=400, detail="Selection exceeds open quantities on table")

    paid_order_ids: list[int] = []
    payment_id = None
    if paid_lines:
        pay_cid = f"partial-{table_number}-{uuid.uuid4().hex[:12]}"
        paid_lines = _lines_with_station_uuid(ev, paid_lines)
        paid_payload = {
            "client_order_id": pay_cid,
            "event_id": body.event_id,
            "table_number": table_number,
            "waiter_uuid": orders[0].waiter_uuid if orders else None,
            "lines": paid_lines,
            "payments": payments,
            "payment_status": "paid",
            "settled_at": now,
            "settlement_table": table_number,
            "partial_settlement": True,
            "voucher_redemptions": voucher_records,
            "voucher_credit_cents": voucher_credit,
            "mode": event_mode_label(str(ev.get("status"))),
        }
        if len(order_discounts_collected) == 1:
            paid_payload["order_discount"] = order_discounts_collected[0]
        order_nums = {int(ln["order_number"]) for ln in paid_lines if ln.get("order_number") is not None}
        if len(order_nums) == 1:
            paid_payload["order_number"] = order_nums.pop()
        sess_id = int(orders[0].session_id) if orders else ensure_order_session(
            db,
            event_id=body.event_id,
            table_number=table_number,
            waiter_uuid=orders[0].waiter_uuid if orders else None,
            order_source="waiter",
        )
        paid_order = LocalOrder(
            session_id=sess_id,
            client_order_id=pay_cid,
            event_id=body.event_id,
            table_number=table_number,
            waiter_uuid=orders[0].waiter_uuid if orders else None,
            payment_status="paid",
            payload_json=json.dumps(paid_payload),
            print_status="done",
        )
        db.add(paid_order)
        db.flush()
        paid_order_ids.append(paid_order.id)
        payment_id = _create_payment_receipt(
            db,
            ev,
            paid_payload,
            source_type="table_partial",
            source_id=paid_order.id,
        ).id
        paid_payload = enrich_payload_for_cloud_sync(
            paid_payload,
            local_order_id=paid_order.id,
            session_id=sess_id,
            mode=event_mode_label(str(ev.get("status"))),
        )
        paid_order.payload_json = json.dumps(paid_payload)
        enqueue_payload_sync(db, event_id=body.event_id, client_order_id=pay_cid, payload=paid_payload)

    db.commit()

    remaining_orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    remaining_cents = 0
    for o in remaining_orders:
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        remaining_cents += order_total_cents(
            lines, payload.get("order_discount"), ev, arts
        )

    return TablePartialSettleResponse(
        paid_cents=expected_cents,
        remaining_cents=remaining_cents,
        paid_order_ids=paid_order_ids,
        payment_id=payment_id,
        table_number=table_number,
        voucher_credit_cents=voucher_credit,
    )


@router.post("/v1/tables/{table_number}/settle", response_model=TableSettleResponse)
def settle_table(
    table_number: int, body: TableSettleBody, db: Session = Depends(get_db)
) -> TableSettleResponse:
    if table_number < 1 or table_number > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == table_number,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")

    payments = dump_payments(body.payments)
    _validate_payment_types(ev, payments)

    now = datetime.now(UTC).isoformat()
    paid_ids = []
    arts = _article_map(ev)
    total_cents = 0
    for o in orders:
        payload = json.loads(o.payload_json)
        lines = payload.get("lines") or []
        cents, _ = _line_totals(lines, arts)
        total_cents += cents

    paid_total = sum(int(p.get("amount_cents") or 0) for p in payments)
    if paid_total != total_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match open balance {total_cents}",
        )

    for o in orders:
        payload = json.loads(o.payload_json)
        payload["payments"] = payments
        payload["payment_status"] = "paid"
        payload["settled_at"] = now
        payload["settlement_table"] = table_number
        o.payment_status = "paid"
        o.payload_json = json.dumps(payload)
        _sync_outbox_payload(db, o, payload)
        paid_ids.append(o.id)

    receipt_payload = _receipt_payload_from_orders(
        ev,
        orders,
        payments,
        table_number=table_number,
        paid_at=now,
    )
    receipt = _create_payment_receipt(
        db,
        ev,
        receipt_payload,
        source_type="table",
        source_id=table_number,
    )
    db.commit()
    return TableSettleResponse(
        paid_order_ids=paid_ids,
        payment_id=receipt.id,
        total_cents=total_cents,
        table_number=table_number,
    )


def _selections_from_body(selections: list[LineSelection]) -> list[dict]:
    return [s.model_dump() for s in selections]


@router.post("/v1/tables/{from_table}/transfer-lines", response_model=TransferLinesResponse)
def transfer_table_lines(
    from_table: int, body: TransferLinesBody, db: Session = Depends(get_db)
) -> TransferLinesResponse:
    if from_table < 1 or from_table > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")
    if body.target_table_number == from_table:
        raise HTTPException(status_code=400, detail="Ziel-Tisch muss ein anderer Tisch sein")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == from_table,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    selections = _selections_from_body(body.selections)
    try:
        moved = take_from_orders(
            db,
            orders,
            selections,
            _sync_outbox_payload,
            transfer_destination={"to_table_number": body.target_table_number},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    waiter_uuid = orders[0].waiter_uuid if orders else None
    append_lines_to_table(
        db,
        ev=ev,
        event_id=body.event_id,
        target_table=body.target_table_number,
        waiter_uuid=waiter_uuid,
        lines=moved,
        lines_with_station=_lines_with_station_uuid,
        sync_outbox=_sync_outbox_payload,
    )
    db.commit()
    return TransferLinesResponse(
        from_table=from_table,
        target_table_number=body.target_table_number,
        moved_line_count=len(moved),
    )


@router.post("/v1/tables/{from_table}/assign-collective", response_model=AssignCollectiveResponse)
def assign_table_to_collective(
    from_table: int, body: AssignCollectiveBody, db: Session = Depends(get_db)
) -> AssignCollectiveResponse:
    if from_table < 1 or from_table > 99999:
        raise HTTPException(status_code=400, detail="table_number must be between 1 and 99999")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")
    if body.collective_bill_id is None and not body.new_name:
        raise HTTPException(status_code=400, detail="collective_bill_id or new_name required")

    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    if body.new_name:
        bill = CollectiveBill(
            uuid=str(uuid.uuid4()),
            event_id=body.event_id,
            name=body.new_name.strip(),
        )
        db.add(bill)
        db.flush()
    else:
        bill = _collective_bill_open(db, body.collective_bill_id, body.event_id)

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.event_id == body.event_id,
            LocalOrder.table_number == from_table,
            LocalOrder.collective_bill_id.is_(None),
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this table")

    selections = _selections_from_body(body.selections)
    try:
        moved = take_from_orders(
            db,
            orders,
            selections,
            _sync_outbox_payload,
            transfer_destination={
                "to_collective_bill_uuid": bill.uuid,
                "to_collective_bill_name": bill.name,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    waiter_uuid = orders[0].waiter_uuid if orders else None
    append_lines_to_collective(
        db,
        ev=ev,
        bill=bill,
        event_id=body.event_id,
        waiter_uuid=waiter_uuid,
        lines=moved,
        lines_with_station=_lines_with_station_uuid,
        sync_outbox=_sync_outbox_payload,
    )
    db.commit()
    return AssignCollectiveResponse(
        collective_bill_id=bill.id,
        collective_bill_uuid=bill.uuid,
        name=bill.name,
        from_table=from_table,
    )


@router.post("/v1/collective-bills", response_model=CollectiveBillCreatedResponse)
def create_collective_bill(
    body: CollectiveBillCreateBody, db: Session = Depends(get_db)
) -> CollectiveBillCreatedResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = CollectiveBill(
        uuid=str(uuid.uuid4()),
        event_id=body.event_id,
        name=body.name.strip(),
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return CollectiveBillCreatedResponse(
        id=bill.id,
        uuid=bill.uuid,
        name=bill.name,
        event_id=bill.event_id,
        total_cents=0,
        order_count=0,
    )


@router.get("/v1/collective-bills/open", response_model=OpenCollectiveBillsResponse)
def list_open_collective_bills(
    event_id: int = Query(...), db: Session = Depends(get_db)
) -> OpenCollectiveBillsResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    arts = _article_map(ev)
    currency = ev.get("currency", "EUR")
    bills = db.query(CollectiveBill).filter(CollectiveBill.event_id == event_id).order_by(CollectiveBill.id.asc()).all()
    result = []
    for bill in bills:
        open_orders = (
            db.query(LocalOrder)
            .filter(
                LocalOrder.collective_bill_id == bill.id,
                LocalOrder.payment_status == "open",
            )
            .all()
        )
        has_any_order = (
            db.query(LocalOrder.id)
            .filter(LocalOrder.collective_bill_id == bill.id)
            .first()
            is not None
        )
        if has_any_order and not open_orders:
            continue
        total_cents = 0
        order_count = distinct_order_numbers_for_local_orders(open_orders)
        item_count = 0
        for o in open_orders:
            payload = json.loads(o.payload_json)
            cents, qty = _line_totals(payload.get("lines") or [], arts)
            total_cents += cents
            item_count += qty
        result.append(
            {
                "id": bill.id,
                "uuid": bill.uuid,
                "name": bill.name,
                "order_count": order_count,
                "total_cents": total_cents,
                "item_count": item_count,
                "currency": currency,
            }
        )
    return OpenCollectiveBillsResponse(
        event_id=event_id, currency=currency, collective_bills=result
    )


@router.get("/v1/collective-bills/{bill_id}", response_model=AccountSummaryResponse)
def get_collective_bill_summary(
    bill_id: int,
    event_id: int = Query(...),
    db: Session = Depends(get_db),
) -> AccountSummaryResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")

    arts = _article_map(ev)
    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )
    summary = _summary_from_orders(
        orders,
        ev,
        arts,
        {
            "collective_bill_id": bill.id,
            "collective_bill_uuid": bill.uuid,
            "name": bill.name,
            "event_id": event_id,
        },
    )
    return AccountSummaryResponse.model_validate(summary)


def _settle_orders_partial(
    db: Session,
    ev: dict,
    body: TableSettlePartialBody,
    orders: list,
    *,
    settlement_meta: dict,
    paid_order_prefix: str,
) -> dict:
    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")
    if not body.selections:
        raise HTTPException(status_code=400, detail="selections required")

    payments = dump_payments(body.payments)
    _validate_payment_types(ev, payments)

    arts = _article_map(ev)
    selections = [s.model_dump() for s in body.selections]

    if not orders:
        raise HTTPException(status_code=404, detail="No open orders")

    line_groups = _build_line_groups_from_orders(orders, arts)
    gross_cents = _selections_total_cents_from_groups(selections, line_groups)
    redemptions_in = [r.model_dump() for r in body.voucher_redemptions]
    voucher_credit, voucher_records = compute_voucher_credits(
        ev,
        gross_cents=gross_cents,
        redemptions=redemptions_in,
        articles=arts,
        selections=selections,
        line_groups=line_groups,
    )
    expected_cents = max(0, gross_cents - voucher_credit)
    paid_total = sum(int(p.get("amount_cents") or 0) for p in payments)
    if paid_total != expected_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match payable {expected_cents}",
        )

    need: dict[tuple, int] = {}
    for s in selections:
        key = _line_key(
            s["article_id"],
            s.get("note", ""),
            s.get("additions"),
            s.get("discount"),
        )
        need[key] = need.get(key, 0) + int(s["qty"])

    paid_lines: list[dict] = []
    order_discounts_collected: list[dict] = []
    now = datetime.now(UTC).isoformat()

    for order in orders:
        payload = json.loads(order.payload_json)
        open_lines: list[dict] = []
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            if is_voucher_sale_line(line):
                continue
            aid = line.get("article_id")
            if aid is None:
                continue
            note = str(line.get("note") or "")
            adds = _normalize_additions(line.get("additions"))
            key = _line_key(aid, note, adds, line.get("discount"))
            qty = max(1, int(line.get("qty") or 1))
            take = min(qty, need.get(key, 0))
            if take > 0:
                pl = {
                    "article_id": int(aid),
                    "qty": take,
                    "note": note,
                    "additions": adds,
                }
                su = line.get("station_uuid")
                if su:
                    pl["station_uuid"] = su
                copy_line_fiscal_fields(line, pl)
                paid_lines.append(pl)
                need[key] = need.get(key, 0) - take
                qty -= take
            if qty > 0:
                open_lines.append({**line, "qty": qty, "additions": adds})
        payload["lines"] = open_lines
        if open_lines:
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)
        else:
            order.payment_status = "paid"
            payload["payment_status"] = "paid"
            payload["settled_at"] = now
            payload.update(settlement_meta)
            order.payload_json = json.dumps(payload)
            _sync_outbox_payload(db, order, payload)
            od = normalize_discount(payload.get("order_discount"))
            if od:
                order_discounts_collected.append(od)

    leftover = sum(v for v in need.values() if v > 0)
    if leftover > 0:
        raise HTTPException(status_code=400, detail="Selection exceeds open quantities")

    paid_order_ids: list[int] = []
    payment_id = None
    if paid_lines:
        pay_cid = f"{paid_order_prefix}-{uuid.uuid4().hex[:12]}"
        paid_lines = _lines_with_station_uuid(ev, paid_lines)
        paid_payload = {
            "client_order_id": pay_cid,
            "event_id": body.event_id,
            "waiter_uuid": orders[0].waiter_uuid if orders else None,
            "lines": paid_lines,
            "payments": payments,
            "payment_status": "paid",
            "settled_at": now,
            "partial_settlement": True,
            "voucher_redemptions": voucher_records,
            "voucher_credit_cents": voucher_credit,
            "mode": event_mode_label(str(ev.get("status"))),
            **settlement_meta,
        }
        if len(order_discounts_collected) == 1:
            paid_payload["order_discount"] = order_discounts_collected[0]
        order_nums = {int(ln["order_number"]) for ln in paid_lines if ln.get("order_number") is not None}
        if len(order_nums) == 1:
            paid_payload["order_number"] = order_nums.pop()
        coll_id = settlement_meta.get("collective_bill_id")
        sess_id = int(orders[0].session_id) if orders else ensure_order_session(
            db,
            event_id=body.event_id,
            table_number=settlement_meta.get("table_number"),
            waiter_uuid=orders[0].waiter_uuid if orders else None,
            order_source="waiter",
        )
        paid_order = LocalOrder(
            session_id=sess_id,
            client_order_id=pay_cid,
            event_id=body.event_id,
            table_number=0 if coll_id else settlement_meta.get("table_number"),
            collective_bill_id=coll_id,
            waiter_uuid=orders[0].waiter_uuid if orders else None,
            payment_status="paid",
            payload_json=json.dumps(paid_payload),
            print_status="done",
        )
        db.add(paid_order)
        db.flush()
        paid_order_ids.append(paid_order.id)
        payment_id = _create_payment_receipt(
            db,
            ev,
            paid_payload,
            source_type="collective_partial" if settlement_meta.get("collective_bill_id") else "table_partial",
            source_id=paid_order.id,
        ).id
        paid_payload = enrich_payload_for_cloud_sync(
            paid_payload,
            local_order_id=paid_order.id,
            session_id=sess_id,
            mode=event_mode_label(str(ev.get("status"))),
        )
        paid_order.payload_json = json.dumps(paid_payload)
        enqueue_payload_sync(db, event_id=body.event_id, client_order_id=pay_cid, payload=paid_payload)

    return {
        "paid_cents": expected_cents,
        "paid_order_ids": paid_order_ids,
        "payment_id": payment_id,
    }


@router.post("/v1/collective-bills/{bill_id}/settle-partial", response_model=CollectivePartialSettleResponse)
def settle_collective_partial(
    bill_id: int,
    body: TableSettlePartialBody,
    db: Session = Depends(get_db),
) -> CollectivePartialSettleResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == body.event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .order_by(LocalOrder.id.asc())
        .all()
    )

    meta = {
        "table_number": None,
        "collective_bill_id": bill.id,
        "collective_bill_uuid": bill.uuid,
        "collective_bill_name": bill.name,
        "settlement_collective_bill_id": bill.id,
    }
    result = _settle_orders_partial(
        db,
        ev,
        body,
        orders,
        settlement_meta=meta,
        paid_order_prefix=f"partial-coll-{bill.id}",
    )
    db.commit()

    remaining_orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    arts = _article_map(ev)
    remaining_cents = 0
    for o in remaining_orders:
        payload = json.loads(o.payload_json)
        cents, _ = _line_totals(payload.get("lines") or [], arts)
        remaining_cents += cents

    return CollectivePartialSettleResponse(
        paid_cents=result["paid_cents"],
        paid_order_ids=result["paid_order_ids"],
        payment_id=result["payment_id"],
        remaining_cents=remaining_cents,
        collective_bill_id=bill.id,
    )


@router.post("/v1/collective-bills/{bill_id}/settle", response_model=CollectiveSettleResponse)
def settle_collective(
    bill_id: int, body: TableSettleBody, db: Session = Depends(get_db)
) -> CollectiveSettleResponse:
    bundle = get_bundle_dict(db)
    ev = event_from_bundle(bundle, body.event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Unknown event_id for cached bundle")

    bill = (
        db.query(CollectiveBill)
        .filter(CollectiveBill.id == bill_id, CollectiveBill.event_id == body.event_id)
        .first()
    )
    if not bill:
        raise HTTPException(status_code=404, detail="Sammelrechnung not found")

    orders = (
        db.query(LocalOrder)
        .filter(
            LocalOrder.collective_bill_id == bill.id,
            LocalOrder.payment_status == "open",
        )
        .all()
    )
    if not orders:
        raise HTTPException(status_code=404, detail="No open orders for this Sammelrechnung")

    if not body.payments:
        raise HTTPException(status_code=400, detail="payments required")

    payments = dump_payments(body.payments)
    _validate_payment_types(ev, payments)

    now = datetime.now(UTC).isoformat()
    arts = _article_map(ev)
    total_cents = 0
    for o in orders:
        payload = json.loads(o.payload_json)
        cents, _ = _line_totals(payload.get("lines") or [], arts)
        total_cents += cents

    paid_total = sum(int(p.get("amount_cents") or 0) for p in payments)
    if paid_total != total_cents:
        raise HTTPException(
            status_code=400,
            detail=f"Payment total {paid_total} does not match open balance {total_cents}",
        )

    meta = {
        "table_number": None,
        "collective_bill_uuid": bill.uuid,
        "collective_bill_name": bill.name,
        "settlement_collective_bill_id": bill.id,
    }
    paid_ids = []
    for o in orders:
        payload = json.loads(o.payload_json)
        payload["payments"] = payments
        payload["payment_status"] = "paid"
        payload["settled_at"] = now
        payload.update(meta)
        o.payment_status = "paid"
        o.payload_json = json.dumps(payload)
        _sync_outbox_payload(db, o, payload)
        paid_ids.append(o.id)

    receipt_payload = _receipt_payload_from_orders(
        ev,
        orders,
        payments,
        collective_bill=bill,
        paid_at=now,
    )
    receipt = _create_payment_receipt(
        db,
        ev,
        receipt_payload,
        source_type="collective",
        source_id=bill.id,
    )
    db.commit()
    return CollectiveSettleResponse(
        paid_order_ids=paid_ids,
        payment_id=receipt.id,
        total_cents=total_cents,
        collective_bill_id=bill.id,
    )

