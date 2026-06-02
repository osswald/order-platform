from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

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
from ..event_collective_bills import build_event_collective_bills_list
from ..vouchers import cell_voucher_uuids_for_read
from ..event_copy import copy_event, default_copy_name
from ..edge_reporting import build_payment_batches_report_v3, build_sales_report_v3
from ..event_sales import build_event_sales_report
from ..payment_types_config import normalize_payment_types, payment_types_from_event
from ..twint_qr import (
    clear_twint_qr,
    has_twint_qr,
    store_twint_qr,
    twint_qr_bytes,
)
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
    currency: str = Field(..., min_length=3, max_length=3)
    organisation_id: int
    payment_mode: str = "pay_later"
    payment_types: List[str] = Field(default_factory=lambda: ["cash"])
    cash_registers_enabled: bool = False
    vouchers_enabled: bool = False

    @model_validator(mode="after")
    def validate_event(self):
        self.status = self.status.lower()
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
        self.currency = self.currency.upper()
        pm = (self.payment_mode or "pay_later").lower()
        if pm not in PAYMENT_MODES:
            raise ValueError(f"payment_mode must be one of: {', '.join(sorted(PAYMENT_MODES))}")
        self.payment_mode = pm
        self.payment_types = normalize_payment_types(self.payment_types)
        if self.end < self.start:
            raise ValueError("End must be after start")
        return self


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1)
    status: str
    start: datetime
    end: datetime
    currency: str = Field(..., min_length=3, max_length=3)
    organisation_id: int | None = None
    payment_mode: str = "pay_later"
    payment_types: List[str] = Field(default_factory=lambda: ["cash"])
    cash_registers_enabled: bool = False
    vouchers_enabled: bool = False

    @model_validator(mode="after")
    def validate_event(self):
        self.status = self.status.lower()
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
        self.currency = self.currency.upper()
        pm = (self.payment_mode or "pay_later").lower()
        if pm not in PAYMENT_MODES:
            raise ValueError(f"payment_mode must be one of: {', '.join(sorted(PAYMENT_MODES))}")
        self.payment_mode = pm
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
    currency: str | None = Field(None, min_length=3, max_length=3)
    organisation_id: int | None = None
    payment_mode: str | None = None
    payment_types: List[str] | None = None
    cash_registers_enabled: bool | None = None
    vouchers_enabled: bool | None = None


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_name: str


class PrinterOptionRead(BaseModel):
    id: int
    name: str


class StationConfigRead(BaseModel):
    uuid: str
    name: str
    sort_order: int
    printer_appliance_id: int | None
    kitchen_monitor_enabled: bool = False
    article_ids: List[int]


class EventWaiterConfigRead(BaseModel):
    uuid: str
    name: str
    pin: str
    source_waiter_id: int | None


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


class EventConfigurationRead(BaseModel):
    stations: List[StationConfigRead]
    event_waiters: List[EventWaiterConfigRead]
    app_layouts: List[AppLayoutRead]
    cash_registers: List[CashRegisterRead]
    voucher_definitions: List[VoucherDefinitionRead] = Field(default_factory=list)
    printer_options: List[PrinterOptionRead]


class StationConfigIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1)
    printer_appliance_id: int | None = None
    kitchen_monitor_enabled: bool = False
    article_ids: List[int] = Field(default_factory=list)


class EventWaiterConfigIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=1)
    source_waiter_id: int | None = None


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


class EventConfigurationIn(BaseModel):
    stations: List[StationConfigIn] = Field(default_factory=list)
    event_waiters: List[EventWaiterConfigIn] = Field(default_factory=list)
    app_layouts: List[AppLayoutIn] = Field(default_factory=list)
    cash_registers: List[CashRegisterIn] = Field(default_factory=list)
    voucher_definitions: List[VoucherDefinitionIn] = Field(default_factory=list)


def event_response(event: Event) -> dict:
    return {
        "id": event.id,
        "name": event.name,
        "status": event.status,
        "start": event.start,
        "end": event.end,
        "currency": event.currency,
        "organisation_id": event.organisation_id,
        "organisation_name": event.organisation.name if event.organisation else "",
        "payment_mode": getattr(event, "payment_mode", None) or "pay_later",
        "payment_types": payment_types_from_event(event),
        "has_twint_qr": has_twint_qr(event),
        "cash_registers_enabled": bool(getattr(event, "cash_registers_enabled", False)),
        "vouchers_enabled": bool(getattr(event, "vouchers_enabled", False)),
    }


def get_event_for_configuration(
    db: Session,
    current_user: User,
    event_id: int,
    hire_company_id: int,
) -> Event:
    event = (
        readable_events_query(db, current_user, hire_company_id)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles),
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
        )
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def serialize_event_configuration(db: Session, event: Event) -> EventConfigurationRead:
    printers = event_printer_candidates(db, event)
    printer_options = [
        PrinterOptionRead(id=a.id, name=(a.name or f"Drucker #{a.id}")) for a in printers
    ]
    stations = []
    for st in sorted(event.stations, key=lambda s: (s.sort_order, s.id)):
        stations.append(
            StationConfigRead(
                uuid=st.uuid,
                name=st.name,
                sort_order=st.sort_order,
                printer_appliance_id=st.printer_appliance_id,
                kitchen_monitor_enabled=bool(getattr(st, "kitchen_monitor_enabled", False)),
                article_ids=[a.id for a in st.articles],
            )
        )
    event_waiters = [
        EventWaiterConfigRead(
            uuid=ew.uuid,
            name=ew.name,
            pin=ew.pin,
            source_waiter_id=ew.source_waiter_id,
        )
        for ew in sorted(event.event_waiters, key=lambda w: w.id)
    ]
    app_layouts = []
    for lo in sorted(event.app_layouts, key=lambda x: x.id):
        cells = []
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
    return EventConfigurationRead(
        stations=stations,
        event_waiters=event_waiters,
        app_layouts=app_layouts,
        cash_registers=cash_registers,
        voucher_definitions=voucher_definitions,
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
    return [{"id": org.id, "name": org.name} for org in readable_organisations(db, current_user, tenant.hire_company_id)]


@router.get("/{event_id}/configuration", response_model=EventConfigurationRead)
def read_event_configuration(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return serialize_event_configuration(db, event)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No TWINT QR code for this event")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enable TWINT in payment types before uploading a QR code",
        )
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        store_twint_qr(event, mime, raw)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
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
        currency=event_in.currency,
        organisation_id=organisation.id,
        payment_mode=event_in.payment_mode,
        payment_types=event_in.payment_types,
        cash_registers_enabled=bool(event_in.cash_registers_enabled),
        vouchers_enabled=bool(event_in.vouchers_enabled),
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event_in.organisation_id is not None:
        organisation = ensure_user_can_use_organisation(db, current_user, event_in.organisation_id, tenant.hire_company_id)
        event.organisation_id = organisation.id
    if event_in.name is not None:
        event.name = event_in.name
    if event_in.status is not None:
        status_value = event_in.status.lower()
        if status_value not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}",
            )
        old_status = event.status
        validate_status_transition(old_status, status_value)
        if old_status == "test" and status_value == "prod":
            purge_event_operational_data(db, event)
        event.status = status_value
    if event_in.start is not None:
        event.start = event_in.start
    if event_in.end is not None:
        event.end = event_in.end
    if event_in.currency is not None:
        event.currency = event_in.currency.upper()
    if event_in.payment_mode is not None:
        pm = event_in.payment_mode.lower()
        if pm not in PAYMENT_MODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"payment_mode must be one of: {', '.join(sorted(PAYMENT_MODES))}",
            )
        event.payment_mode = pm
    if event_in.payment_types is not None:
        try:
            new_types = normalize_payment_types(event_in.payment_types)
            event.payment_types = new_types
            if "twint" not in new_types:
                clear_twint_qr(event)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            ) from e
    if event_in.cash_registers_enabled is not None:
        event.cash_registers_enabled = bool(event_in.cash_registers_enabled)
    if event_in.vouchers_enabled is not None:
        event.vouchers_enabled = bool(event_in.vouchers_enabled)
    if event.end < event.start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="End must be after start")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    db.delete(event)
    db.commit()
    return None
