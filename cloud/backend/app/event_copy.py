"""Duplicate an event configuration without sales or collective-bill data."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from sqlalchemy.orm import Session, joinedload

from .event_config_validation import replace_event_configuration
from .instant_collective_bill import apply_instant_collective_bill_settings
from .models import (
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventArticleStock,
    EventStation,
)
from .payment_types_config import payment_types_from_event
from .stock import upsert_stock_rows
from .vouchers import cell_voucher_uuids_for_read


def _load_event_for_copy(db: Session, event_id: int) -> Event | None:
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.stations).joinedload(EventStation.printer_rules),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles),
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
            joinedload(Event.kitchen_monitor_printers),
        )
        .filter(Event.id == event_id)
        .first()
    )


def _stations_payload(event: Event) -> list:
    out = []
    for st in sorted(event.stations, key=lambda s: (s.sort_order, s.id)):
        rules = []
        for rule in sorted(st.printer_rules or [], key=lambda r: (r.sort_order, r.id)):
            rules.append(
                SimpleNamespace(
                    sort_order=rule.sort_order,
                    rule_type=rule.rule_type,
                    table_from=rule.table_from,
                    table_to=rule.table_to,
                    pickup_prefix=rule.pickup_prefix,
                    printer_appliance_id=rule.printer_appliance_id,
                )
            )
        out.append(
            SimpleNamespace(
                uuid=None,
                name=st.name,
                printer_appliance_id=st.printer_appliance_id,
                article_ids=[a.id for a in st.articles],
                printer_rules=rules,
            )
        )
    return out


def _kitchen_monitors_payload(event: Event) -> list:
    return [
        SimpleNamespace(
            printer_appliance_id=row.printer_appliance_id,
            sort_order=row.sort_order,
            label=row.label,
        )
        for row in sorted(event.kitchen_monitor_printers or [], key=lambda r: (r.sort_order, r.id))
    ]


def _waiters_payload(event: Event) -> list:
    return [
        SimpleNamespace(
            uuid=None,
            name=ew.name,
            pin=ew.pin,
            source_waiter_id=ew.source_waiter_id,
            subsidiary_code=getattr(ew, "subsidiary_code", None),
        )
        for ew in sorted(event.event_waiters, key=lambda w: w.id)
    ]


def _vouchers_payload(event: Event) -> tuple[list, dict[str, str]]:
    out = []
    uuid_map: dict[str, str] = {}
    for vd in sorted(event.voucher_definitions, key=lambda v: (v.sort_order, v.id)):
        new_uuid = str(uuid.uuid4())
        uuid_map[str(vd.uuid)] = new_uuid
        out.append(
            SimpleNamespace(
                uuid=new_uuid,
                name=vd.name,
                kind=vd.kind,
                value_cents=vd.value_cents,
                allowed_article_ids=list(vd.allowed_article_ids or []),
                include_additions=bool(vd.include_additions),
            )
        )
    return out, uuid_map


def _layouts_payload(event: Event, voucher_uuid_map: dict[str, str]) -> tuple[list, dict[str, str]]:
    out = []
    uuid_map: dict[str, str] = {}
    for lo in sorted(event.app_layouts, key=lambda x: x.id):
        new_uuid = str(uuid.uuid4())
        uuid_map[str(lo.uuid)] = new_uuid
        cells = []
        for cell in sorted(lo.cells, key=lambda c: (c.row, c.col)):
            old_uuids = cell_voucher_uuids_for_read(cell)
            new_uuids = [voucher_uuid_map.get(str(u), str(u)) for u in old_uuids if u]
            new_uuids = [u for u in new_uuids if u]
            cells.append(
                SimpleNamespace(
                    row=cell.row,
                    col=cell.col,
                    label=cell.label or "",
                    color=cell.color or "#eeeeee",
                    article_ids=[a.id for a in cell.articles],
                    voucher_definition_uuid=new_uuids[0] if new_uuids else None,
                    voucher_definition_uuids=new_uuids,
                )
            )
        out.append(
            SimpleNamespace(
                uuid=new_uuid,
                name=lo.name,
                is_default=bool(lo.is_default),
                grid_width=lo.grid_width,
                grid_height=lo.grid_height,
                cells=cells,
            )
        )
    return out, uuid_map


def _cash_registers_payload(event: Event, layout_uuid_map: dict[str, str]) -> list:
    out = []
    for reg in sorted(event.cash_registers, key=lambda r: (r.sort_order, r.id)):
        new_layout_uuid = layout_uuid_map.get(str(reg.layout_uuid))
        if not new_layout_uuid:
            continue
        out.append(
            SimpleNamespace(
                uuid=None,
                name=reg.name,
                pickup_code_prefix=reg.pickup_code_prefix,
                pin=getattr(reg, "pin", None) or "0000",
                layout_uuid=new_layout_uuid,
                receipt_printer_appliance_id=reg.receipt_printer_appliance_id,
                cash_drawer_command=getattr(reg, "cash_drawer_command", None) or "none",
                subsidiary_code=getattr(reg, "subsidiary_code", None),
            )
        )
    return out


def default_copy_name(source_name: str) -> str:
    base = (source_name or "").strip() or "Event"
    suffix = " (Kopie)"
    if base.endswith(suffix):
        return base
    return f"{base}{suffix}"


def copy_event(db: Session, source: Event, *, name: str) -> Event:
    """Clone event config onto a new Event row. Caller must have loaded source relations."""
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")

    new_event = Event(
        name=name,
        status="config",
        start=source.start,
        end=source.end,
        organisation_id=source.organisation_id,
        payment_mode=getattr(source, "payment_mode", None) or "pay_later",
        payment_types=list(payment_types_from_event(source)),
        cash_registers_enabled=bool(getattr(source, "cash_registers_enabled", False)),
        shift_settlement_enabled=bool(getattr(source, "shift_settlement_enabled", False)),
        vouchers_enabled=bool(getattr(source, "vouchers_enabled", False)),
        discounts_enabled=bool(getattr(source, "discounts_enabled", False)),
        alternative_printers_enabled=bool(getattr(source, "alternative_printers_enabled", False)),
        kitchen_monitors_enabled=bool(getattr(source, "kitchen_monitors_enabled", False)),
        offer_payment_receipt=bool(getattr(source, "offer_payment_receipt", False)),
    )
    apply_instant_collective_bill_settings(
        new_event,
        payment_mode=new_event.payment_mode,
        instant_collective_bill_name=getattr(source, "instant_collective_bill_name", None),
        payment_mode_set=True,
        instant_collective_bill_name_set=True,
    )
    if source.twint_qr_mime and source.twint_qr_data:
        new_event.twint_qr_mime = source.twint_qr_mime
        new_event.twint_qr_data = source.twint_qr_data
    from .receipt_printing_config import copy_receipt_printing

    copy_receipt_printing(source, new_event, include_event_label=True)

    db.add(new_event)
    db.flush()

    source_stock = (
        db.query(EventArticleStock).filter(EventArticleStock.event_id == source.id).all()
    )
    stock_by_article = {r.article_id: r for r in source_stock}

    vouchers_payload, voucher_uuid_map = _vouchers_payload(source)
    layouts_payload, layout_uuid_map = _layouts_payload(source, voucher_uuid_map)

    replace_event_configuration(
        db,
        new_event,
        stations_in=_stations_payload(source),
        event_waiters_in=_waiters_payload(source),
        app_layouts_in=layouts_payload,
        cash_registers_in=_cash_registers_payload(source, layout_uuid_map),
        voucher_definitions_in=vouchers_payload,
        kitchen_monitors_in=_kitchen_monitors_payload(source),
    )

    from .additions import event_stock_article_ids
    from .ingredients import (
        event_stock_article_ids_with_additions,
        organisation_ingredients_enabled,
    )

    if organisation_ingredients_enabled(db, new_event.organisation_id):
        allowed = event_stock_article_ids_with_additions(db, new_event)
    else:
        allowed = event_stock_article_ids(db, new_event)
    stock_items = []
    for aid in sorted(allowed):
        row = stock_by_article.get(aid)
        if not row:
            continue
        stock_items.append(
            {
                "article_id": aid,
                "monitor_stock": row.monitor_stock,
                "in_stock": row.in_stock,
                "initial_in_stock": row.baseline_in_stock,
            }
        )
    if stock_items:
        upsert_stock_rows(db, new_event, stock_items)

    from .ingredient_stock import upsert_ingredient_stock_rows
    from .ingredients import ingredient_ids_for_event, organisation_ingredients_enabled
    from .models import EventIngredientStock

    if organisation_ingredients_enabled(db, new_event.organisation_id):
        source_ing_stock = (
            db.query(EventIngredientStock).filter(EventIngredientStock.event_id == source.id).all()
        )
        stock_by_ingredient = {r.ingredient_id: r for r in source_ing_stock}
        allowed_ing = ingredient_ids_for_event(db, new_event)
        ing_items = []
        for iid in sorted(allowed_ing):
            row = stock_by_ingredient.get(iid)
            if not row:
                continue
            ing_items.append(
                {
                    "ingredient_id": iid,
                    "monitor_stock": row.monitor_stock,
                    "in_stock": float(row.in_stock) if row.in_stock is not None else None,
                    "initial_in_stock": float(row.baseline_in_stock)
                    if row.baseline_in_stock is not None
                    else None,
                }
            )
        if ing_items:
            upsert_ingredient_stock_rows(db, new_event, ing_items)

    db.flush()
    return new_event
