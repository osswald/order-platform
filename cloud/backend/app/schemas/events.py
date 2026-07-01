"""Event API Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..event_status import ALLOWED_STATUSES
from ..payment_types_config import normalize_payment_types

PAYMENT_MODES = {"instant", "pay_now", "pay_later"}

class EventBase(BaseModel):
    name: str = Field(..., min_length=1)
    status: str
    start: datetime
    end: datetime
    organisation_id: int
    payment_mode: str = "pay_later"
    payment_types: list[str] = Field(default_factory=lambda: ["cash"])
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
    payment_types: list[str] = Field(default_factory=lambda: ["cash"])
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
    payment_types: list[str] | None = None
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
    organisation_currency: str = "EUR"
    organisation_country_code: str = "CH"


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
    article_ids: list[int]
    printer_rules: list[StationPrinterRuleRead] = Field(default_factory=list)


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
    allowed_article_ids: list[int] = Field(default_factory=list)
    include_additions: bool = True
    sort_order: int = 0


class LayoutCellRead(BaseModel):
    row: int
    col: int
    label: str
    color: str
    article_ids: list[int]
    voucher_definition_uuid: str | None = None
    voucher_definition_uuids: list[str] = Field(default_factory=list)


class AppLayoutRead(BaseModel):
    id: int
    uuid: str
    name: str | None
    is_default: bool
    grid_width: int
    grid_height: int
    cells: list[LayoutCellRead]


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
    stations: list[StationConfigRead]
    event_waiters: list[EventWaiterConfigRead]
    app_layouts: list[AppLayoutRead]
    cash_registers: list[CashRegisterRead]
    voucher_definitions: list[VoucherDefinitionRead] = Field(default_factory=list)
    kitchen_monitors: list[KitchenMonitorPrinterRead] = Field(default_factory=list)
    printer_options: list[PrinterOptionRead]


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
    article_ids: list[int] = Field(default_factory=list)
    printer_rules: list[StationPrinterRuleIn] = Field(default_factory=list)


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
    allowed_article_ids: list[int] = Field(default_factory=list)
    include_additions: bool = True


class LayoutCellIn(BaseModel):
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)
    label: str = ""
    color: str = "#eeeeee"
    article_ids: list[int] = Field(default_factory=list)
    voucher_definition_uuid: str | None = None
    voucher_definition_uuids: list[str] = Field(default_factory=list)


class AppLayoutIn(BaseModel):
    uuid: str | None = None
    name: str | None = None
    is_default: bool = False
    grid_width: int = Field(..., ge=1, le=64)
    grid_height: int = Field(..., ge=1, le=64)
    cells: list[LayoutCellIn] = Field(default_factory=list)


class CashRegisterIn(BaseModel):
    uuid: str | None = None
    name: str = Field(..., min_length=1)
    pickup_code_prefix: str = Field(..., min_length=1, max_length=3)
    pin: str = Field("0000", min_length=1, max_length=32)
    layout_uuid: str = Field(..., min_length=1)
    receipt_printer_appliance_id: int | None = None
    subsidiary_code: str | None = Field(None, max_length=32)


class EventConfigurationIn(BaseModel):
    stations: list[StationConfigIn] = Field(default_factory=list)
    event_waiters: list[EventWaiterConfigIn] = Field(default_factory=list)
    app_layouts: list[AppLayoutIn] = Field(default_factory=list)
    cash_registers: list[CashRegisterIn] = Field(default_factory=list)
    voucher_definitions: list[VoucherDefinitionIn] = Field(default_factory=list)
    kitchen_monitors: list[KitchenMonitorPrinterIn] = Field(default_factory=list)
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
    additions: list[SalesAdditionLineRead] = Field(default_factory=list)


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
    lines: list[SalesOrderLineRead] = Field(default_factory=list)
    payments: list[SalesPaymentRead] = Field(default_factory=list)


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
    orders: list[SalesOrderRead]
    by_waiter: list[SalesByWaiterRead]
    by_station: list[SalesByStationRead]
    by_article: list[SalesByArticleRead]
    by_payment_type: list[SalesByPaymentTypeRead]

class CollectiveBillOrderRead(BaseModel):
    id: int
    client_order_id: str
    order_number: int | None = None
    created_at: str | None = None
    payment_status: str
    line_cents: int
    paid_cents: int
    lines: list[dict] = []
    payments: list[dict] = []


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
    line_groups: list[dict] = []
    orders: list[CollectiveBillOrderRead] = []


class EventCollectiveBillsListRead(BaseModel):
    currency: str
    country_code: str = "CH"
    collective_bills: list[CollectiveBillRead]
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
    lines: list[dict] = []
    moved_lines: list[dict] = []


class EventTransactionsPageRead(BaseModel):
    currency: str
    country_code: str = "CH"
    total: int
    page: int
    items_per_page: int
    items: list[TransactionRead]
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
    ledger: list[dict] = []
    payments_by_method: dict = {}
    vouchers_by_definition: dict = {}


class EventCashSessionsPageRead(BaseModel):
    currency: str
    country_code: str = "CH"
    total: int
    page: int
    items_per_page: int
    items: list[CashSessionRead]
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
    country_code: str = "CH"
    totals: V3SalesTotalsRead
    by_waiter: list[V3SalesByWaiterRead]
    by_station: list[V3SalesByStationRead]
    by_article: list[V3SalesByArticleRead]
    by_payment_type: list[V3SalesByPaymentTypeRead]


class StatsTotalsRead(BaseModel):
    distinct_orders_count: int
    line_cents: int
    paid_cents: int
    open_cents: int
    average_order_value_cents: int


class StatsTimelineBucketRead(BaseModel):
    start: str
    end: str
    label: str


class StatsArticleSeriesRead(BaseModel):
    article_id: int
    name: str
    qty: list[int]


class StatsArticleTotalRead(BaseModel):
    article_id: int
    name: str
    qty: int


class StatsArticleTimelineRead(BaseModel):
    bucket_count: int
    buckets: list[StatsTimelineBucketRead]
    series: list[StatsArticleSeriesRead]
    totals: list[StatsArticleTotalRead]


class StatsCategorySeriesRead(BaseModel):
    category_id: int
    name: str
    qty: list[int]


class StatsCategoryTotalRead(BaseModel):
    category_id: int
    name: str
    qty: int


class StatsCategoryTimelineRead(BaseModel):
    bucket_count: int
    buckets: list[StatsTimelineBucketRead]
    series: list[StatsCategorySeriesRead]
    totals: list[StatsCategoryTotalRead]


class StatsRevenueTimelineRead(BaseModel):
    bucket_count: int
    buckets: list[StatsTimelineBucketRead]
    line_cents: list[int]


class StatsTopArticleRead(BaseModel):
    article_id: int
    name: str
    qty: int
    line_cents: int


class StatsByOrderSourceRead(BaseModel):
    source: str
    label: str
    qty: int
    line_cents: int


class StatsByWaiterRead(BaseModel):
    name: str
    order_count: int
    qty: int
    line_cents: int
    paid_cents: int


class StatsByStationRead(BaseModel):
    name: str
    qty: int
    line_cents: int


class StatsByPaymentTypeRead(BaseModel):
    type: str
    label: str
    amount_cents: int


class EventStatsRead(BaseModel):
    currency: str
    country_code: str = "CH"
    from_: str = Field(alias="from")
    to: str
    bucket_count: int
    totals: StatsTotalsRead
    revenue_timeline: StatsRevenueTimelineRead
    top_articles: list[StatsTopArticleRead]
    by_order_source: list[StatsByOrderSourceRead]
    article_timeline: StatsArticleTimelineRead
    category_timeline: StatsCategoryTimelineRead
    by_payment_type: list[StatsByPaymentTypeRead]
    by_waiter: list[StatsByWaiterRead]
    by_station: list[StatsByStationRead]

    model_config = {"populate_by_name": True}


class PaymentBatchV3Read(BaseModel):
    uuid: str
    name: str
    status: str
    created_at: str | None = None
    closed_at: str | None = None
    total_cents: int


class EventPaymentBatchesV3Read(BaseModel):
    currency: str
    country_code: str = "CH"
    payment_batches: list[PaymentBatchV3Read]
