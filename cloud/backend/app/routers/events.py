from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from ..i18n.errors import api_error
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..appliance_naming import appliance_display_name
from ..event_config_validation import (
    build_station_article_tree,
    event_printer_candidates,
    replace_event_configuration,
)
from ..models import (
    Article,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventCashRegister,
    EventArticleStock,
    EventStation,
    Organisation,
    User,
)
from ..currency import event_currency
from ..event_cash_sessions import build_cash_sessions_page
from ..event_transactions import build_event_transactions_page
from ..vouchers import cell_voucher_uuids_for_read
from ..event_copy import copy_event, default_copy_name
from ..event_bookkeeping import build_event_bookkeeping_report
from ..event_sales import build_event_sales_report
from ..payment_types_config import normalize_payment_types, payment_types_from_event
from ..twint_qr import (
    clear_twint_qr,
    has_twint_qr,
    store_twint_qr,
    twint_qr_bytes,
)
from ..instant_collective_bill import apply_instant_collective_bill_settings, instant_collective_bill_fields
from ..event_status import ALLOWED_STATUSES, assert_create_status, purge_event_operational_data, validate_status_transition
from ..stock import ensure_stock_rows_for_event_articles, normalize_stock_fields, upsert_stock_rows
from ..auth_deps import get_current_user
from ..deps import get_db
from ..tenancy import (
    TenantContext,
    ensure_user_can_use_organisation,
    get_current_tenant,
    get_current_tenant_admin,
    readable_events_query,
    readable_organisations,
)

router = APIRouter()

PAYMENT_MODES = {"instant", "pay_now", "pay_later"}


class EventBase(BaseModel):
    name: str = Field(..., min_length=1)
    status: str
    start: datetime
    end: datetime
    organisation_id: int
    payment_mode: str = "pay_later"
    payment_types: List[str] = Field(default_factory=lambda: ["cash"])
    cash_registers_enabled: bool = False
    shift_settlement_enabled: bool = False
    vouchers_enabled: bool = False
    discounts_enabled: bool = False
    alternative_printers_enabled: bool = False
    kitchen_monitors_enabled: bool = False
    offer_payment_receipt: bool = False
    instant_collective_bill_name: str | None = None
    instant_collective_bill_uuid: str | None = None

    @model_validator(mode="after")
    def validate_event(self):
        self.status = self.status.lower()
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
        pm = (self.payment_mode or "pay_later").lower()
        if pm not in PAYMENT_MODES:
            raise ValueError(f"payment_mode must be one of: {', '.join(sorted(PAYMENT_MODES))}")
        self.payment_mode = pm
        if pm == "instant" and not str(self.instant_collective_bill_name or "").strip():
            raise ValueError("instant_collective_bill_name is required when payment_mode is instant")
        self.payment_types = normalize_payment_types(self.payment_types)
        if self.end < self.start:
            raise ValueError("End must be after start")
        return self


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1)
    status: str
    start: datetime
    end: datetime
    organisation_id: int | None = None
    payment_mode: str = "pay_later"
    payment_types: List[str] = Field(default_factory=lambda: ["cash"])
    cash_registers_enabled: bool = False
    shift_settlement_enabled: bool = False
    vouchers_enabled: bool = False
    discounts_enabled: bool = False
    alternative_printers_enabled: bool = False
    kitchen_monitors_enabled: bool = False
    offer_payment_receipt: bool = False
    instant_collective_bill_name: str | None = None
    instant_collective_bill_uuid: str | None = None

    @model_validator(mode="after")
    def validate_event(self):
        self.status = self.status.lower()
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
        pm = (self.payment_mode or "pay_later").lower()
        if pm not in PAYMENT_MODES:
            raise ValueError(f"payment_mode must be one of: {', '.join(sorted(PAYMENT_MODES))}")
        self.payment_mode = pm
        if pm == "instant" and not str(self.instant_collective_bill_name or "").strip():
            raise ValueError("instant_collective_bill_name is required when payment_mode is instant")
        self.payment_types = normalize_payment_types(self.payment_types)
        if self.end < self.start:
            raise ValueError("End must be after start")
        return self


class EventCopyIn(BaseModel):
    name: str | None = Field(None, min_length=1)


class EventUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    status: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    organisation_id: int | None = None
    payment_mode: str | None = None
    payment_types: List[str] | None = None
    cash_registers_enabled: bool | None = None
    shift_settlement_enabled: bool | None = None
    vouchers_enabled: bool | None = None
    discounts_enabled: bool | None = None
    alternative_printers_enabled: bool | None = None
    kitchen_monitors_enabled: bool | None = None
    offer_payment_receipt: bool | None = None
    instant_collective_bill_name: str | None = None


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_name: str


class PrinterOptionRead(BaseModel):
    id: int
    name: str


class StationPrinterRuleRead(BaseModel):
    sort_order: int
    rule_type: str
    table_from: int | None = None
    table_to: int | None = None
    pickup_prefix: str | None = None
    printer_appliance_id: int | None


class KitchenMonitorPrinterRead(BaseModel):
    printer_appliance_id: int
    sort_order: int
    label: str | None = None


class StationConfigRead(BaseModel):
    uuid: str
    name: str
    sort_order: int
    printer_appliance_id: int | None
    article_ids: List[int]
    printer_rules: List[StationPrinterRuleRead] = Field(default_factory=list)


class EventWaiterConfigRead(BaseModel):
    uuid: str
    name: str
    pin: str
    source_waiter_id: int | None
    subsidiary_code: str | None = None


class VoucherDefinitionRead(BaseModel):
    uuid: str
    name: str
    kind: str
    value_cents: int | None = None
    allowed_article_ids: List[int] = Field(default_factory=list)
    include_additions: bool = True
    sort_order: int = 0


class LayoutCellRead(BaseModel):
    row: int
    col: int
    label: str
    color: str
    article_ids: List[int]
    voucher_definition_uuid: str | None = None
    voucher_definition_uuids: List[str] = Field(default_factory=list)


class AppLayoutRead(BaseModel):
    id: int
    uuid: str
    name: str | None
    is_default: bool
    grid_width: int
    grid_height: int
    cells: List[LayoutCellRead]


class CashRegisterRead(BaseModel):
    uuid: str
    name: str
    sort_order: int
    pickup_code_prefix: str
    pin: str
    layout_uuid: str
    receipt_printer_appliance_id: int | None
    subsidiary_code: str | None = None


class EventConfigurationRead(BaseModel):
    stations: List[StationConfigRead]
    event_waiters: List[EventWaiterConfigRead]
    app_layouts: List[AppLayoutRead]
    cash_registers: List[CashRegisterRead]
    voucher_definitions: List[VoucherDefinitionRead] = Field(default_factory=list)
    kitchen_monitors: List[KitchenMonitorPrinterRead] = Field(default_factory=list)
    printer_options: List[PrinterOptionRead]


class StationPrinterRuleIn(BaseModel):
    sort_order: int = 0
    rule_type: str = Field(..., min_length=1)
    table_from: int | None = Field(None, ge=1, le=99999)
    table_to: int | None = Field(None, ge=1, le=99999)
    pickup_prefix: str | None = Field(None, min_length=1, max_length=3)
    printer_appliance_id: int | None = None


class KitchenMonitorPrinterIn(BaseModel):
    printer_appliance_id: int
    sort_order: int = 0
    label: str | None = Field(None, max_length=128)


class StationConfigIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1)
    printer_appliance_id: int | None = None
    article_ids: List[int] = Field(default_factory=list)
    printer_rules: List[StationPrinterRuleIn] = Field(default_factory=list)


class EventWaiterConfigIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=1)
    source_waiter_id: int | None = None
    subsidiary_code: str | None = Field(None, max_length=32)


class VoucherDefinitionIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1, max_length=128)
    kind: str = Field(..., min_length=1, max_length=32)
    value_cents: int | None = Field(None, ge=1)
    allowed_article_ids: List[int] = Field(default_factory=list)
    include_additions: bool = True


class LayoutCellIn(BaseModel):
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)
    label: str = ""
    color: str = "#eeeeee"
    article_ids: List[int] = Field(default_factory=list)
    voucher_definition_uuid: str | None = None
    voucher_definition_uuids: List[str] = Field(default_factory=list)


class AppLayoutIn(BaseModel):
    uuid: str | None = None
    name: str | None = None
    is_default: bool = False
    grid_width: int = Field(..., ge=1, le=64)
    grid_height: int = Field(..., ge=1, le=64)
    cells: List[LayoutCellIn] = Field(default_factory=list)


class CashRegisterIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1)
    pickup_code_prefix: str = Field(..., min_length=1, max_length=3)
    pin: str = Field("0000", min_length=1, max_length=32)
    layout_uuid: str = Field(..., min_length=1)
    receipt_printer_appliance_id: int | None = None
    subsidiary_code: str | None = Field(None, max_length=32)


class EventConfigurationIn(BaseModel):
    stations: List[StationConfigIn] = Field(default_factory=list)
    event_waiters: List[EventWaiterConfigIn] = Field(default_factory=list)
    app_layouts: List[AppLayoutIn] = Field(default_factory=list)
    cash_registers: List[CashRegisterIn] = Field(default_factory=list)
    voucher_definitions: List[VoucherDefinitionIn] = Field(default_factory=list)
    kitchen_monitors: List[KitchenMonitorPrinterIn] = Field(default_factory=list)


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
    layout_load = (
        joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles)
        if include_layout_cells
        else joinedload(Event.app_layouts)
    )
    event = (
        readable_events_query(db, current_user, hire_company_id)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            layout_load,
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
            joinedload(Event.kitchen_monitor_printers),
            joinedload(Event.stations).joinedload(EventStation.printer_rules),
        )
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


@router.get("/", response_model=List[EventRead])
def read_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    events = readable_events_query(db, current_user, tenant.hire_company_id).order_by(Event.start.desc()).all()
    return [event_response(event) for event in events]


@router.get("/organisations")
def read_event_organisations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return [
        {
            "id": org.id,
            "name": org.name,
            "currency": org.currency,
            "country_id": org.country_id,
            "vat_liable": bool(org.vat_liable),
            "default_tax_code_id": org.default_tax_code_id,
            "accounts_enabled": bool(org.accounts_enabled),
        }
        for org in readable_organisations(db, current_user, tenant.hire_company_id)
    ]


@router.get("/{event_id}/configuration", response_model=EventConfigurationRead)
def read_event_configuration(
    event_id: int,
    fields: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    include_layout_cells = fields != "summary"
    event = get_event_for_configuration(
        db,
        current_user,
        event_id,
        tenant.hire_company_id,
        include_layout_cells=include_layout_cells,
    )
    return serialize_event_configuration(db, event, include_layout_cells=include_layout_cells)


@router.get("/{event_id}/station-article-tree")
def read_event_station_article_tree(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return {"nodes": build_station_article_tree(db, event)}


class EventStockItemRead(BaseModel):
    id: int
    name: str
    label: str
    monitor_stock: bool
    in_stock: int | None = None


class EventStockListRead(BaseModel):
    items: List[EventStockItemRead]


class EventStockItemIn(BaseModel):
    article_id: int
    monitor_stock: bool = False
    in_stock: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def normalize(self):
        monitor, qty = normalize_stock_fields(self.monitor_stock, self.in_stock)
        self.monitor_stock = monitor
        self.in_stock = qty
        return self


class EventStockUpdateIn(BaseModel):
    items: List[EventStockItemIn] = Field(default_factory=list)


class SalesAdditionLineRead(BaseModel):
    article_id: int
    name: str
    qty: int
    line_cents: int


class SalesOrderLineRead(BaseModel):
    article_id: int
    name: str
    qty: int
    station_uuid: str | None = None
    station_name: str
    line_cents: int
    additions: List[SalesAdditionLineRead] = Field(default_factory=list)


class SalesPaymentRead(BaseModel):
    type: str
    type_label: str
    amount_cents: int


class SalesOrderRead(BaseModel):
    id: int
    client_order_id: str
    created_at: str | None = None
    table_number: Any = None
    waiter_uuid: str | None = None
    waiter_name: str
    payment_status: str
    line_cents: int
    paid_cents: int
    lines: List[SalesOrderLineRead] = Field(default_factory=list)
    payments: List[SalesPaymentRead] = Field(default_factory=list)


class SalesTotalsRead(BaseModel):
    orders_count: int
    line_cents: int
    paid_cents: int
    open_cents: int


class SalesByWaiterRead(BaseModel):
    waiter_uuid: str | None = None
    name: str
    line_cents: int
    paid_cents: int
    order_count: int


class SalesByStationRead(BaseModel):
    station_uuid: str | None = None
    name: str
    line_cents: int
    qty: int


class SalesByArticleRead(BaseModel):
    article_id: int
    name: str
    qty: int
    line_cents: int


class SalesByPaymentTypeRead(BaseModel):
    type: str
    label: str
    amount_cents: int


class EventSalesReportRead(BaseModel):
    currency: str
    totals: SalesTotalsRead
    orders: List[SalesOrderRead]
    by_waiter: List[SalesByWaiterRead]
    by_station: List[SalesByStationRead]
    by_article: List[SalesByArticleRead]
    by_payment_type: List[SalesByPaymentTypeRead]


@router.get("/{event_id}/sales-report", response_model=EventSalesReportRead)
def read_event_sales_report(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_event_sales_report(db, event)


class CollectiveBillOrderRead(BaseModel):
    id: int
    client_order_id: str
    order_number: int | None = None
    created_at: str | None = None
    payment_status: str
    line_cents: int
    paid_cents: int
    lines: List[dict] = []
    payments: List[dict] = []


class CollectiveBillRead(BaseModel):
    uuid: str
    name: str
    status: str
    created_at: str | None = None
    closed_at: str | None = None
    order_count: int
    line_cents: int
    open_cents: int
    paid_cents: int
    line_groups: List[dict] = []
    orders: List[CollectiveBillOrderRead] = []


class EventCollectiveBillsListRead(BaseModel):
    currency: str
    collective_bills: List[CollectiveBillRead]


@router.get("/{event_id}/collective-bills", response_model=EventCollectiveBillsListRead)
def read_event_collective_bills(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_event_collective_bills_list(db, event)


class TransactionRead(BaseModel):
    id: int
    created_at: str | None = None
    kind: str
    client_order_id: str
    table_number: int | None = None
    collective_bill_name: str | None = None
    waiter_name: str
    payment_status: str
    line_cents: int
    moved_line_cents: int = 0
    paid_cents: int
    payment_methods: str
    line_count: int
    lines: List[dict] = []
    moved_lines: List[dict] = []


class EventTransactionsPageRead(BaseModel):
    currency: str
    total: int
    page: int
    items_per_page: int
    items: List[TransactionRead]


@router.get("/{event_id}/transactions", response_model=EventTransactionsPageRead)
def read_event_transactions(
    event_id: int,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(25, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_desc: bool = Query(True),
    payment_status: str | None = Query(None),
    kind: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_event_transactions_page(
        db,
        event,
        page=page,
        items_per_page=items_per_page,
        sort_by=sort_by,
        sort_desc=sort_desc,
        payment_status=payment_status,
        kind=kind,
    )


class CashSessionRead(BaseModel):
    id: int
    cash_session_id: int
    subject_type: str
    subject_name: str
    operator_waiter_name: str
    status: str
    opening_balance_cents: int
    wallet_cents: int
    total_cash_cents: int
    total_non_cash_cents: int
    counted_cash_cents: int | None = None
    variance_cents: int | None = None
    started_at: str | None = None
    ended_at: str | None = None
    ledger: List[dict] = []
    payments_by_method: dict = {}
    vouchers_by_definition: dict = {}


class EventCashSessionsPageRead(BaseModel):
    currency: str
    total: int
    page: int
    items_per_page: int
    items: List[CashSessionRead]


@router.get("/{event_id}/cash-sessions", response_model=EventCashSessionsPageRead)
def read_event_cash_sessions(
    event_id: int,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(25, ge=1, le=200),
    sort_by: str = Query("started_at"),
    sort_desc: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_cash_sessions_page(
        db,
        event,
        page=page,
        items_per_page=items_per_page,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


class V3SalesTotalsRead(BaseModel):
    distinct_orders_count: int
    line_cents: int
    paid_cents: int
    open_cents: int


class V3SalesByWaiterRead(BaseModel):
    name: str
    order_count: int
    line_cents: int
    paid_cents: int


class V3SalesByStationRead(BaseModel):
    name: str
    qty: int
    line_cents: int


class V3SalesByArticleRead(BaseModel):
    name: str
    qty: int
    line_cents: int


class V3SalesByPaymentTypeRead(BaseModel):
    type: str
    label: str
    amount_cents: int


class EventSalesReportV3Read(BaseModel):
    currency: str
    totals: V3SalesTotalsRead
    by_waiter: list[V3SalesByWaiterRead]
    by_station: list[V3SalesByStationRead]
    by_article: list[V3SalesByArticleRead]
    by_payment_type: list[V3SalesByPaymentTypeRead]


@router.get("/{event_id}/sales-report-v3", response_model=EventSalesReportV3Read)
def read_event_sales_report_v3(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_sales_report_v3(db, organisation_id=event.organisation_id, event_id=event.id)


class PaymentBatchV3Read(BaseModel):
    uuid: str
    name: str
    status: str
    created_at: str | None = None
    closed_at: str | None = None
    total_cents: int


class EventPaymentBatchesV3Read(BaseModel):
    currency: str
    payment_batches: list[PaymentBatchV3Read]


@router.get("/{event_id}/payment-batches-v3", response_model=EventPaymentBatchesV3Read)
def read_event_payment_batches_v3(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_payment_batches_report_v3(db, organisation_id=event.organisation_id, event_id=event.id)


@router.get("/{event_id}/bookkeeping")
def read_event_bookkeeping(
    event_id: int,
    view: str = Query("both", pattern="^(summary|detail|both)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    result = build_event_bookkeeping_report(
        db,
        organisation_id=event.organisation_id,
        event_id=event.id,
        view=view,
    )
    if result.get("error") == "event_not_found":
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    if result.get("error") == "accounts_not_enabled":
        raise api_error("accounts_not_enabled", status.HTTP_409_CONFLICT)
    return result


@router.get("/{event_id}/twint-qr")
def get_event_twint_qr(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    payload = twint_qr_bytes(event)
    if not payload:
        raise api_error("no_twint_qr", status.HTTP_404_NOT_FOUND)
    mime, raw = payload
    return Response(content=raw, media_type=mime)


@router.put("/{event_id}/twint-qr")
async def put_event_twint_qr(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    if "twint" not in payment_types_from_event(event):
        raise api_error("enable_twint_before_qr", status.HTTP_400_BAD_REQUEST)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        store_twint_qr(event, mime, raw)
    except ValueError as e:
        raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST) from e
    db.commit()
    db.refresh(event)
    return {"ok": True, "has_twint_qr": True}


@router.delete("/{event_id}/twint-qr", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_twint_qr(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    clear_twint_qr(event)
    db.commit()


@router.get("/{event_id}/event-stock", response_model=EventStockListRead)
def read_event_stock(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    rows = ensure_stock_rows_for_event_articles(db, event, commit=True)
    art_by_id = {a.id: a for a in db.query(Article).filter(Article.id.in_([r.article_id for r in rows])).all()}
    items = []
    for row in rows:
        art = art_by_id.get(row.article_id)
        if not art:
            continue
        items.append(
            EventStockItemRead(
                id=art.id,
                name=art.name,
                label=art.label,
                monitor_stock=row.monitor_stock,
                in_stock=row.in_stock,
            )
        )
    items.sort(key=lambda x: x.name.lower())
    return EventStockListRead(items=items)


@router.put("/{event_id}/event-stock", response_model=EventStockListRead)
def put_event_stock(
    event_id: int,
    body: EventStockUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    try:
        upsert_stock_rows(
            db,
            event,
            [{"article_id": i.article_id, "monitor_stock": i.monitor_stock, "in_stock": i.in_stock} for i in body.items],
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    rows = (
        db.query(EventArticleStock)
        .filter(EventArticleStock.event_id == event.id)
        .all()
    )
    art_by_id = {a.id: a for a in db.query(Article).filter(Article.id.in_([r.article_id for r in rows])).all()}
    items = []
    for row in rows:
        art = art_by_id.get(row.article_id)
        if not art:
            continue
        items.append(
            EventStockItemRead(
                id=art.id,
                name=art.name,
                label=art.label,
                monitor_stock=row.monitor_stock,
                in_stock=row.in_stock,
            )
        )
    items.sort(key=lambda x: x.name.lower())
    return EventStockListRead(items=items)


@router.put("/{event_id}/configuration", response_model=EventConfigurationRead)
def put_event_configuration(
    event_id: int,
    body: EventConfigurationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    try:
        replace_event_configuration(
            db,
            event,
            stations_in=body.stations,
            event_waiters_in=body.event_waiters,
            app_layouts_in=body.app_layouts,
            cash_registers_in=body.cash_registers,
            voucher_definitions_in=body.voucher_definitions,
            kitchen_monitors_in=body.kitchen_monitors,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return serialize_event_configuration(db, event)


@router.get("/{event_id}", response_model=EventRead)
def read_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = readable_events_query(db, current_user, tenant.hire_company_id).filter(Event.id == event_id).first()
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    return event_response(event)


@router.post("/", response_model=EventRead)
def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    organisation = ensure_user_can_use_organisation(db, current_user, event_in.organisation_id, tenant.hire_company_id)
    create_status = assert_create_status(event_in.status)
    event = Event(
        name=event_in.name,
        status=create_status,
        start=event_in.start,
        end=event_in.end,
        organisation_id=organisation.id,
        payment_mode=event_in.payment_mode,
        payment_types=event_in.payment_types,
        cash_registers_enabled=bool(event_in.cash_registers_enabled),
        shift_settlement_enabled=bool(event_in.shift_settlement_enabled),
        vouchers_enabled=bool(event_in.vouchers_enabled),
        discounts_enabled=bool(event_in.discounts_enabled),
        alternative_printers_enabled=bool(event_in.alternative_printers_enabled),
        kitchen_monitors_enabled=bool(event_in.kitchen_monitors_enabled),
        offer_payment_receipt=bool(event_in.offer_payment_receipt),
    )
    apply_instant_collective_bill_settings(
        event,
        payment_mode=event_in.payment_mode,
        instant_collective_bill_name=event_in.instant_collective_bill_name,
        payment_mode_set=True,
        instant_collective_bill_name_set=True,
    )
    db.add(event)
    db.flush()
    from ..receipt_printing_config import copy_receipt_printing_from_organisation

    copy_receipt_printing_from_organisation(organisation, event)
    db.commit()
    db.refresh(event)
    return event_response(event)


@router.post("/{event_id}/copy", response_model=EventRead)
def copy_event_endpoint(
    event_id: int,
    body: EventCopyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    source = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    copy_name = (body.name or "").strip() or default_copy_name(source.name)
    try:
        new_event = copy_event(db, source, name=copy_name)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT) from e
    except Exception:
        db.rollback()
        raise
    new_event = get_event_for_configuration(db, current_user, new_event.id, tenant.hire_company_id)
    return event_response(new_event)


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = readable_events_query(db, current_user, tenant.hire_company_id).filter(Event.id == event_id).first()
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)

    if event_in.organisation_id is not None:
        organisation = ensure_user_can_use_organisation(db, current_user, event_in.organisation_id, tenant.hire_company_id)
        event.organisation_id = organisation.id
    if event_in.name is not None:
        event.name = event_in.name
    if event_in.status is not None:
        status_value = event_in.status.lower()
        if status_value not in ALLOWED_STATUSES:
            raise api_error("status_must_be_one_of", status.HTTP_422_UNPROCESSABLE_CONTENT, statuses=", ".join(sorted(ALLOWED_STATUSES)))
        old_status = event.status
        validate_status_transition(old_status, status_value)
        if old_status == "test" and status_value == "prod":
            purge_event_operational_data(db, event)
        event.status = status_value
    if event_in.start is not None:
        event.start = event_in.start
    if event_in.end is not None:
        event.end = event_in.end
    if event_in.payment_mode is not None:
        pm = event_in.payment_mode.lower()
        if pm not in PAYMENT_MODES:
            raise api_error("payment_mode_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT, modes=", ".join(sorted(PAYMENT_MODES)))
        event.payment_mode = pm
    if event_in.instant_collective_bill_name is not None:
        event.instant_collective_bill_name = event_in.instant_collective_bill_name
    apply_instant_collective_bill_settings(
        event,
        payment_mode=event.payment_mode,
        instant_collective_bill_name=event.instant_collective_bill_name,
        payment_mode_set=event_in.payment_mode is not None,
        instant_collective_bill_name_set=event_in.instant_collective_bill_name is not None,
    )
    if event_in.payment_types is not None:
        try:
            new_types = normalize_payment_types(event_in.payment_types)
            event.payment_types = new_types
            if "twint" not in new_types:
                clear_twint_qr(event)
        except ValueError as e:
            raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT) from e
    if event_in.cash_registers_enabled is not None:
        event.cash_registers_enabled = bool(event_in.cash_registers_enabled)
    if event_in.shift_settlement_enabled is not None:
        event.shift_settlement_enabled = bool(event_in.shift_settlement_enabled)
    if event_in.vouchers_enabled is not None:
        event.vouchers_enabled = bool(event_in.vouchers_enabled)
    if event_in.discounts_enabled is not None:
        event.discounts_enabled = bool(event_in.discounts_enabled)
    if event_in.alternative_printers_enabled is not None:
        event.alternative_printers_enabled = bool(event_in.alternative_printers_enabled)
    if event_in.kitchen_monitors_enabled is not None:
        event.kitchen_monitors_enabled = bool(event_in.kitchen_monitors_enabled)
    if event_in.offer_payment_receipt is not None:
        event.offer_payment_receipt = bool(event_in.offer_payment_receipt)
    if event.end < event.start:
        raise api_error("end_must_be_after_start", status.HTTP_422_UNPROCESSABLE_CONTENT)

    db.commit()
    db.refresh(event)
    return event_response(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    event = (
        readable_events_query(db, current_user, tenant.hire_company_id)
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    db.delete(event)
    db.commit()
    return None
