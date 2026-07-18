"""Shared order, payment, and account-summary models for the Pi edge API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DiscountKind = Literal["percent", "amount"]


class DiscountIn(BaseModel):
    kind: DiscountKind
    value: int = Field(..., ge=0)


class LineAdditionIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    article_id: int
    qty: int = Field(1, ge=1)
    name: str | None = None
    label: str | None = None


class OrderLineIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    article_id: int | None = None
    qty: int = Field(1, ge=1)
    note: str = ""
    additions: list[LineAdditionIn] = Field(default_factory=list)
    discount: DiscountIn | None = None
    station_uuid: str | None = None
    kind: str | None = None
    voucher_definition_uuid: str | None = None
    voucher_name: str | None = None
    value_cents: int | None = None
    article_name: str | None = None


class PaymentIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    amount_cents: int = Field(..., ge=0)
    stripe_payment_intent_id: str | None = None


class OpenOrderEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    local_order_id: int
    client_order_id: str
    created_at: str | None = None
    lines: list[OrderLineIn] = Field(default_factory=list)
    line_total_cents: int
    order_discount: DiscountIn | None = None


class LineGroupEntry(BaseModel):
    kind: Literal["article", "voucher_sale"] = "article"
    article_id: int | None = None
    voucher_definition_uuid: str | None = None
    name: str | None = None
    note: str = ""
    additions: list[LineAdditionIn] = Field(default_factory=list)
    discount: DiscountIn | None = None
    total_qty: int = Field(..., ge=1)
    unit_cents: int = Field(..., ge=0)
    line_total_cents: int = Field(..., ge=0)


class ArticleStockPatch(BaseModel):
    model_config = ConfigDict(extra="allow")

    in_stock: int | None = None
    sellable: bool | None = None
    monitor_stock: bool | None = None


class RegisterDisplayPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    state: str | None = None
    total_cents: int | None = None
    lines: list[OrderLineIn] = Field(default_factory=list)


class KitchenTicketLineEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    line_index: int
    line: OrderLineIn
    qty_total: int = Field(..., ge=0)
    qty_printed: int = Field(..., ge=0)
    qty_remaining: int = Field(..., ge=0)


def dump_lines(lines: list[OrderLineIn]) -> list[dict]:
    return [line.model_dump(exclude_none=True) for line in lines]


def dump_payments(payments: list[PaymentIn]) -> list[dict]:
    return [payment.model_dump(exclude_none=True) for payment in payments]


def dump_discount(discount: DiscountIn | None) -> dict | None:
    return discount.model_dump() if discount else None
