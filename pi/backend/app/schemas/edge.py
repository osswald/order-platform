"""Request and response models for the Pi edge API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Request bodies ---


class LocalOrderCreate(BaseModel):
    client_order_id: str = Field(..., min_length=8, max_length=64)
    event_id: int
    table_number: int | None = Field(None, ge=1, le=99999)
    waiter_uuid: str | None = None
    order_source: str = "waiter"
    cash_register_uuid: str | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)
    payments: list[dict[str, Any]] = Field(default_factory=list)


class RegisterDisplayBody(BaseModel):
    event_id: int
    payload: dict[str, Any] = Field(default_factory=dict)


class OrderPayBody(BaseModel):
    payments: list[dict[str, Any]] = Field(default_factory=list)


class TableSettleBody(BaseModel):
    event_id: int
    payments: list[dict[str, Any]] = Field(default_factory=list)


class LineSelection(BaseModel):
    article_id: int
    note: str = ""
    qty: int = Field(..., ge=1)
    additions: list[dict[str, Any]] = Field(default_factory=list)


class TableSettlePartialBody(BaseModel):
    event_id: int
    payments: list[dict[str, Any]] = Field(default_factory=list)
    selections: list[LineSelection] = Field(default_factory=list)


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


class PrinterTestReceiptBody(BaseModel):
    event_id: int | None = None


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
    articles: dict[str, Any] = Field(default_factory=dict)


class KitchenStationItem(BaseModel):
    uuid: str
    name: str
    sort_order: int


class KitchenStationsResponse(BaseModel):
    stations: list[KitchenStationItem]


class KitchenTicketPrintResponse(BaseModel):
    print_job_id: int | None
    ticket_status: str


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
    payload: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class EscposPayloadResponse(BaseModel):
    escpos_payload: str


class PaymentReceiptEscposResponse(BaseModel):
    payment_id: int
    escpos_payload: str


class PrintJobSummary(BaseModel):
    id: int
    local_order_id: int | None
    printer_host: str | None
    status: str | None
    last_error: str | None
