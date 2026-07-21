"""Shared helpers for event routers."""

from fastapi import status
from sqlalchemy.orm import Session, joinedload, selectinload

from ..appliance_naming import appliance_display_name
from ..currency import event_country_code, event_currency
from ..event_config_validation import event_printer_candidates
from ..i18n.errors import api_error
from ..instant_collective_bill import instant_collective_bill_fields
from ..models import (
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventStation,
    User,
)
from ..payment_types_config import payment_types_from_event
from ..schemas.events import (
    AppLayoutRead,
    CashRegisterRead,
    EventConfigurationRead,
    EventWaiterConfigRead,
    KitchenMonitorPrinterRead,
    LayoutCellRead,
    PrinterOptionRead,
    StationConfigRead,
    StationPrinterRuleRead,
    VoucherDefinitionRead,
)
from ..tenancy import readable_events_query
from ..twint_qr import has_twint_qr
from ..vouchers import cell_voucher_uuids_for_read


def event_configuration_load_options(*, include_layout_cells: bool = True):
    """Eager-load options for configuration reads.

    Collection relationships use selectinload to avoid a cartesian JOIN product
    from stacking multiple joinedload() collections on one query.
    """
    layout_load = (
        selectinload(Event.app_layouts)
        .selectinload(EventAppLayout.cells)
        .selectinload(EventAppLayoutCell.articles)
        if include_layout_cells
        else selectinload(Event.app_layouts)
    )
    return (
        joinedload(Event.organisation),
        selectinload(Event.stations).selectinload(EventStation.articles),
        selectinload(Event.stations).selectinload(EventStation.printer_rules),
        selectinload(Event.event_waiters),
        layout_load,
        selectinload(Event.cash_registers),
        selectinload(Event.voucher_definitions),
        selectinload(Event.kitchen_monitor_printers),
    )


def event_station_article_tree_load_options():
    """Minimal load for station-article-tree (stations → articles only)."""
    return (
        selectinload(Event.stations).selectinload(EventStation.articles),
    )


def event_response(event: Event) -> dict:
    return {
        "id": event.id,
        "name": event.name,
        "status": event.status,
        "start": event.start,
        "end": event.end,
        "organisation_id": event.organisation_id,
        "organisation_name": event.organisation.name if event.organisation else "",
        "organisation_currency": event_currency(event, "EUR"),
        "organisation_country_code": event_country_code(event, "CH"),
        "payment_mode": getattr(event, "payment_mode", None) or "pay_later",
        "payment_types": payment_types_from_event(event),
        "has_twint_qr": has_twint_qr(event),
        "cash_registers_enabled": bool(getattr(event, "cash_registers_enabled", False)),
        "shift_settlement_enabled": bool(getattr(event, "shift_settlement_enabled", False)),
        "vouchers_enabled": bool(getattr(event, "vouchers_enabled", False)),
        "discounts_enabled": bool(getattr(event, "discounts_enabled", False)),
        "alternative_printers_enabled": bool(getattr(event, "alternative_printers_enabled", False)),
        "kitchen_monitors_enabled": bool(getattr(event, "kitchen_monitors_enabled", False)),
        "offer_payment_receipt": bool(getattr(event, "offer_payment_receipt", False)),
        **instant_collective_bill_fields(event),
    }


def get_event_for_configuration(
    db: Session,
    current_user: User,
    event_id: int,
    hire_company_id: int,
    *,
    include_layout_cells: bool = True,
) -> Event:
    event = (
        readable_events_query(db, current_user, hire_company_id)
        .options(*event_configuration_load_options(include_layout_cells=include_layout_cells))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    return event


def get_event_for_station_article_tree(
    db: Session,
    current_user: User,
    event_id: int,
    hire_company_id: int,
) -> Event:
    event = (
        readable_events_query(db, current_user, hire_company_id)
        .options(*event_station_article_tree_load_options())
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    return event


def serialize_event_configuration(
    db: Session,
    event: Event,
    *,
    include_layout_cells: bool = True,
) -> EventConfigurationRead:
    printers = event_printer_candidates(db, event)
    printer_options = [
        PrinterOptionRead(id=a.id, name=appliance_display_name(a) or f"Drucker #{a.id}") for a in printers
    ]
    stations = []
    for st in sorted(event.stations, key=lambda s: (s.sort_order, s.id)):
        stations.append(
            StationConfigRead(
                uuid=st.uuid,
                name=st.name,
                sort_order=st.sort_order,
                printer_appliance_id=st.printer_appliance_id,
                article_ids=[a.id for a in st.articles],
                printer_rules=[
                    StationPrinterRuleRead(
                        sort_order=rule.sort_order,
                        rule_type=rule.rule_type,
                        table_from=rule.table_from,
                        table_to=rule.table_to,
                        pickup_prefix=rule.pickup_prefix,
                        printer_appliance_id=rule.printer_appliance_id,
                    )
                    for rule in sorted(st.printer_rules or [], key=lambda r: (r.sort_order, r.id))
                ],
            )
        )
    event_waiters = [
        EventWaiterConfigRead(
            uuid=ew.uuid,
            name=ew.name,
            pin=ew.pin,
            source_waiter_id=ew.source_waiter_id,
            subsidiary_code=getattr(ew, "subsidiary_code", None),
        )
        for ew in sorted(event.event_waiters, key=lambda w: w.id)
    ]
    app_layouts = []
    for lo in sorted(event.app_layouts, key=lambda x: x.id):
        cells = []
        if include_layout_cells:
            for cell in sorted(lo.cells, key=lambda c: (c.row, c.col)):
                v_uuids = cell_voucher_uuids_for_read(cell)
                cells.append(
                    LayoutCellRead(
                        row=cell.row,
                        col=cell.col,
                        label=cell.label or "",
                        color=cell.color or "#eeeeee",
                        article_ids=[a.id for a in cell.articles],
                        voucher_definition_uuid=v_uuids[0] if v_uuids else None,
                        voucher_definition_uuids=v_uuids,
                    )
                )
        app_layouts.append(
            AppLayoutRead(
                id=lo.id,
                uuid=lo.uuid,
                name=lo.name,
                is_default=bool(lo.is_default),
                grid_width=lo.grid_width,
                grid_height=lo.grid_height,
                cells=cells,
            )
        )
    cash_registers = [
        CashRegisterRead(
            uuid=reg.uuid,
            name=reg.name,
            sort_order=reg.sort_order,
            pickup_code_prefix=reg.pickup_code_prefix,
            pin=getattr(reg, "pin", None) or "0000",
            layout_uuid=reg.layout_uuid,
            receipt_printer_appliance_id=reg.receipt_printer_appliance_id,
            cash_drawer_command=getattr(reg, "cash_drawer_command", None) or "none",
            subsidiary_code=getattr(reg, "subsidiary_code", None),
        )
        for reg in sorted(event.cash_registers, key=lambda r: (r.sort_order, r.id))
    ]
    voucher_definitions = [
        VoucherDefinitionRead(
            uuid=vd.uuid,
            name=vd.name,
            kind=vd.kind,
            value_cents=vd.value_cents,
            allowed_article_ids=list(vd.allowed_article_ids or []),
            include_additions=bool(vd.include_additions),
            sort_order=vd.sort_order,
        )
        for vd in sorted(event.voucher_definitions, key=lambda v: (v.sort_order, v.id))
    ]
    kitchen_monitors = [
        KitchenMonitorPrinterRead(
            printer_appliance_id=row.printer_appliance_id,
            sort_order=row.sort_order,
            label=row.label,
        )
        for row in sorted(event.kitchen_monitor_printers or [], key=lambda r: (r.sort_order, r.id))
    ]
    return EventConfigurationRead(
        stations=stations,
        event_waiters=event_waiters,
        app_layouts=app_layouts,
        cash_registers=cash_registers,
        voucher_definitions=voucher_definitions,
        kitchen_monitors=kitchen_monitors,
        printer_options=printer_options,
    )
