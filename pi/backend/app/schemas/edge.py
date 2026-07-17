"""Request and response models for the Pi edge API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .order_models import (
    ArticleStockPatch,
    DiscountIn,
    KitchenTicketLineEntry,
    LineAdditionIn,
    LineGroupEntry,
    OpenOrderEntry,
    OrderLineIn,
    PaymentIn,
    RegisterDisplayPayload,
)

ReceiptPaperWidth = Literal["80mm", "58mm", "53mm"]
ReceiptCharset = Literal["pc858", "pc850", "cp1252", "ascii"]


# --- Request bodies ---


class VoucherRedemptionIn(BaseModel):
    voucher_definition_uuid: str = Field(..., min_length=1)
    article_id: int | None = None
    note: str = ""
    qty: int = Field(1, ge=1)
    additions: list[LineAdditionIn] = Field(default_factory=list)


class StockValidateLineIn(BaseModel):
    article_id: int
    qty: int = Field(..., ge=1)
    additions: list[LineAdditionIn] = Field(default_factory=list)


class StockValidateOrderIn(BaseModel):
    event_id: int
    lines: list[StockValidateLineIn] = Field(default_factory=list)


class StockValidateOrderResponse(BaseModel):
    ok: bool = True


class LocalOrderCreate(BaseModel):
    client_order_id: str = Field(..., min_length=8, max_length=64)
    event_id: int
    table_number: int | None = Field(None, ge=1, le=99999)
    waiter_uuid: str | None = None
    order_source: str = "waiter"
    cash_register_uuid: str | None = None
    lines: list[OrderLineIn] = Field(default_factory=list)
    order_discount: DiscountIn | None = None
    payments: list[PaymentIn] = Field(default_factory=list)
    voucher_redemptions: list[VoucherRedemptionIn] = Field(default_factory=list)


class RegisterDisplayBody(BaseModel):
    event_id: int
    payload: RegisterDisplayPayload = Field(default_factory=RegisterDisplayPayload)


class OrderPayBody(BaseModel):
    payments: list[PaymentIn] = Field(default_factory=list)


class TableSettleBody(BaseModel):
    event_id: int
    payments: list[PaymentIn] = Field(default_factory=list)


class LineSelection(BaseModel):
    article_id: int
    note: str = ""
    qty: int = Field(..., ge=1)
    additions: list[LineAdditionIn] = Field(default_factory=list)
    discount: DiscountIn | None = None


class TableSettlePartialBody(BaseModel):
    event_id: int
    payments: list[PaymentIn] = Field(default_factory=list)
    selections: list[LineSelection] = Field(default_factory=list)
    voucher_redemptions: list[VoucherRedemptionIn] = Field(default_factory=list)


class TransferLinesBody(BaseModel):
    event_id: int
    target_table_number: int = Field(..., ge=1, le=99999)
    selections: list[LineSelection] = Field(default_factory=list)


class AssignCollectiveBody(BaseModel):
    event_id: int
    selections: list[LineSelection] = Field(default_factory=list)
    collective_bill_id: int | None = None
    new_name: str | None = Field(None, min_length=1, max_length=128)


class CollectiveBillCreateBody(BaseModel):
    event_id: int
    name: str = Field(..., min_length=1, max_length=128)


class PaymentReceiptBody(BaseModel):
    reprint: bool = False
    paper_width: ReceiptPaperWidth | None = None
    charset: ReceiptCharset | None = None


class PaymentReceiptPrintBody(BaseModel):
    station_uuid: str = Field(..., min_length=1, max_length=36)


class PrinterTestReceiptBody(BaseModel):
    event_id: int | None = None
    paper_width: ReceiptPaperWidth | None = None
    charset: ReceiptCharset | None = None


class PrinterTestStationPrintsBody(BaseModel):
    event_id: int


class AdminVerifyBody(BaseModel):
    pin: str = Field(..., min_length=6, max_length=6)


# --- Responses ---


class OkResponse(BaseModel):
    ok: bool = True


class SyncMetaResponse(BaseModel):
    last_sync_at: str | None


class SyncPullResponse(BaseModel):
    ok: bool = True
    event_count: int


class SyncPushError(BaseModel):
    client_order_id: str
    error: str


class SyncPushResponse(BaseModel):
    sent: int
    errors: list[SyncPushError] = Field(default_factory=list)


class CloudReachableResponse(BaseModel):
    reachable: bool
    reason: str | None = None


class SyncStatusResponse(BaseModel):
    """Mirrors sync_service.sync_status plus per-request fields."""

    model_config = ConfigDict(extra="allow")

    configured: bool
    pending_outbox_count: int
    bundle_last_sync_at: str | None


class AdminStatusResponse(BaseModel):
    bundle_ready: bool
    requires_pin: bool


class OrderPayResponse(BaseModel):
    local_order_id: int
    payment_id: int
    payment_status: str


class LocalOrderCreatedResponse(BaseModel):
    local_order_id: int
    payment_id: int | None = None
    order_number: str | int | None = None
    print_job_id: int | None = None
    print_job_ids: list[int] = Field(default_factory=list)
    customer_print_job_ids: list[int] = Field(default_factory=list)
    kitchen_ticket_ids: list[int] = Field(default_factory=list)
    payment_status: str
    pickup_code: str | None = None
    pickup_status: str | None = None
    payment_mode: str
    articles: dict[str, ArticleStockPatch] = Field(default_factory=dict)
    ingredients: dict[str, ArticleStockPatch] = Field(default_factory=dict)


class KitchenStationItem(BaseModel):
    uuid: str
    name: str
    sort_order: int


class KitchenPrinterItem(BaseModel):
    printer_appliance_id: int
    label: str
    sort_order: int


class KitchenPrintersResponse(BaseModel):
    printers: list[KitchenPrinterItem]


class KitchenStationsResponse(BaseModel):
    stations: list[KitchenStationItem]


class KitchenTicketPrintResponse(BaseModel):
    print_job_id: int | None
    ticket_status: str


class KitchenTicketPartialPrintLine(BaseModel):
    line_id: int
    qty: int = Field(..., ge=1)


class KitchenTicketPartialPrintBody(BaseModel):
    lines: list[KitchenTicketPartialPrintLine] = Field(..., min_length=1)


class PickupOrderItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    local_order_id: int
    client_order_id: str
    pickup_code: str | None = None
    pickup_status: str
    cash_register_uuid: str | None = None
    cash_register_name: str | None = None
    order_number: str | int | None = None
    created_at: str | None = None
    ready_at: str | None = None
    item_count: int


class PickupOrdersResponse(BaseModel):
    orders: list[PickupOrderItem]


class PickupPickedUpResponse(BaseModel):
    local_order_id: int
    pickup_status: str


class RegisterDisplayResponse(BaseModel):
    cash_register_uuid: str
    event_id: int
    payload: RegisterDisplayPayload = Field(default_factory=RegisterDisplayPayload)
    updated_at: str | None = None


class EscposPayloadResponse(BaseModel):
    escpos_payload: str


class StationTestPrintResult(BaseModel):
    station_uuid: str
    station_name: str
    printer_host: str
    printer_port: int
    ok: bool
    error: str | None = None


class PrinterTestStationPrintsResponse(BaseModel):
    event_id: int
    printed: int
    failed: int
    results: list[StationTestPrintResult] = Field(default_factory=list)


class PaymentReceiptEscposResponse(BaseModel):
    payment_id: int
    escpos_payload: str


class PaymentReceiptPrintResponse(BaseModel):
    ok: bool = True
    print_job_id: int


class PrintJobSummary(BaseModel):
    id: int
    local_order_id: int | None = None
    printer_host: str | None = None
    status: str | None = None
    last_error: str | None = None
    station_uuid: str | None = None
    station_name: str | None = None
    table_number: int | None = None
    order_number: int | None = None
    job_kind: str | None = None
    event_id: int | None = None
    created_at: str | None = None


class PrintJobRetryResponse(BaseModel):
    ok: bool = True
    print_job_id: int
    status: str


class OpenTableRow(BaseModel):
    table_number: int
    order_count: int
    total_cents: int
    item_count: int
    currency: str


class OpenTablesResponse(BaseModel):
    event_id: int
    currency: str
    tables: list[OpenTableRow]


class AccountSummaryResponse(BaseModel):
    """Table or collective-bill open balance summary."""

    model_config = ConfigDict(extra="allow")

    currency: str
    open_orders: list[OpenOrderEntry]
    line_groups: list[LineGroupEntry]
    total_cents: int
    item_count: int


class TableSettleResponse(BaseModel):
    paid_order_ids: list[int]
    payment_id: int
    total_cents: int
    table_number: int


class PartialSettleResponse(BaseModel):
    paid_cents: int
    paid_order_ids: list[int]
    payment_id: int


class TablePartialSettleResponse(PartialSettleResponse):
    remaining_cents: int
    table_number: int
    voucher_credit_cents: int = 0


class OrderPartialSettleResponse(PartialSettleResponse):
    remaining_cents: int
    local_order_id: int
    voucher_credit_cents: int = 0


class OrderAssignCollectiveResponse(BaseModel):
    collective_bill_id: int
    collective_bill_uuid: str
    name: str
    local_order_id: int


class RegisterOpenOrderRow(BaseModel):
    local_order_id: int
    client_order_id: str
    pickup_code: str | None = None
    total_cents: int
    item_count: int
    created_at: str | None = None


class RegisterOpenOrdersResponse(BaseModel):
    event_id: int
    currency: str
    orders: list[RegisterOpenOrderRow]


class TransferLinesResponse(BaseModel):
    from_table: int
    target_table_number: int
    moved_line_count: int


class AssignCollectiveResponse(BaseModel):
    collective_bill_id: int
    collective_bill_uuid: str
    name: str
    from_table: int


class CollectiveBillCreatedResponse(BaseModel):
    id: int
    uuid: str
    name: str
    event_id: int
    total_cents: int
    order_count: int


class CollectiveBillListItem(BaseModel):
    id: int
    uuid: str
    name: str
    order_count: int
    total_cents: int
    item_count: int
    currency: str


class OpenCollectiveBillsResponse(BaseModel):
    event_id: int
    currency: str
    collective_bills: list[CollectiveBillListItem]


class CollectivePartialSettleResponse(PartialSettleResponse):
    remaining_cents: int
    collective_bill_id: int


class CollectiveSettleResponse(BaseModel):
    paid_order_ids: list[int]
    payment_id: int
    total_cents: int
    collective_bill_id: int


class KitchenOrderTicket(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    local_order_id: int
    event_id: int
    station_uuid: str
    status: str
    lines: list[KitchenTicketLineEntry]


class KitchenOrdersResponse(BaseModel):
    orders: list[KitchenOrderTicket]


class PaymentListItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    payment_id: int
    total_cents: int
    item_count: int
    currency: str


class PaymentsListResponse(BaseModel):
    payments: list[PaymentListItem]


class ShiftSessionOpenBody(BaseModel):
    event_id: int
    subject_type: Literal["waiter", "cash_register"]
    waiter_uuid: str | None = None
    cash_register_uuid: str | None = None
    operator_waiter_uuid: str | None = None
    opening_balance_cents: int = Field(0, ge=0)


class ShiftSessionCloseBody(BaseModel):
    counted_cash_cents: int = Field(..., ge=0)
    station_uuid: str | None = None
    paper_width: ReceiptPaperWidth | None = None
    charset: ReceiptCharset | None = None


class ShiftSessionReceiptBody(BaseModel):
    counted_cash_cents: int | None = Field(None, ge=0)
    paper_width: ReceiptPaperWidth | None = None
    charset: ReceiptCharset | None = None


class ShiftSessionRead(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    event_id: int
    subject_type: str
    subject_name: str
    status: str
    opening_balance_cents: int
    wallet_cents: int
    total_cash_cents: int
    total_non_cash_cents: int
    started_at: str | None = None


class ShiftSessionEscposResponse(BaseModel):
    cash_session_id: int
    escpos_payload: str


class ShiftSessionPrintResponse(BaseModel):
    ok: bool
    print_job_id: int | None = None
