"""Pydantic schemas for Orderjutsu event import."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .events import EventConfigurationRead, EventRead


class OrderjutsuImportPreviewRequest(BaseModel):
    organisation_id: int
    payload: dict[str, Any]


class OrderjutsuImportPreviewEvent(BaseModel):
    name: str
    start: datetime
    end: datetime
    currency: str
    currency_matches_org: bool


class OrderjutsuImportPreviewProduct(BaseModel):
    ref: int
    label: str
    bon_text: str
    price: float
    is_addition: bool
    monitor_stock: bool
    stock: int
    is_voucher: bool
    ingredient_only: bool
    is_composite: bool
    match_kind: Literal["import_number", "exact", "ambiguous", "none"]
    matched_article_id: int | None = None
    matched_article_name: str | None = None
    matched_article_price: float | None = None
    ambiguous_article_ids: list[int] = Field(default_factory=list)


class OrderjutsuImportPreviewCashier(BaseModel):
    index: int
    label: str
    pin: str
    is_extra: bool
    table_prefix: str | None = None
    has_custom_layout: bool = False
    auto_table: bool = False
    match_kind: Literal["exact", "none"]
    matched_waiter_id: int | None = None
    matched_waiter_name: str | None = None


class OrderjutsuImportPreviewStation(BaseModel):
    index: int
    label: str
    product_refs: list[int] = Field(default_factory=list)
    printer_loc: str | None = None
    printer_type: str | None = None


class OrderjutsuImportPreviewLayoutSummary(BaseModel):
    name: str
    grid_width: int
    grid_height: int
    cell_count: int
    is_default: bool = False
    source_cashier_index: int | None = None


class OrderjutsuImportPreviewExtra(BaseModel):
    product_ref: int
    extra_ref: int


class OrderjutsuImportPreviewStockCandidate(BaseModel):
    ref: int
    bon_text: str
    monitor_stock: bool
    stock: int
    kind: Literal["article", "ingredient"]


class OrderjutsuImportPreviewVoucher(BaseModel):
    ref: int
    label: str
    price: float


class OrderjutsuImportPreviewRecipeRow(BaseModel):
    product_ref: int
    product_bon_text: str
    ingredient_ref: int
    ingredient_bon_text: str
    amount: float


class OrderjutsuImportPreviewIngredient(BaseModel):
    ref: int
    bon_text: str
    match_kind: Literal["exact", "none"]
    matched_ingredient_id: int | None = None
    matched_ingredient_name: str | None = None


class OrderjutsuImportPreviewWarning(BaseModel):
    code: str
    message: str


class OrderjutsuImportPreview(BaseModel):
    event: OrderjutsuImportPreviewEvent
    products: list[OrderjutsuImportPreviewProduct]
    cashiers: list[OrderjutsuImportPreviewCashier]
    stations: list[OrderjutsuImportPreviewStation]
    layouts: list[OrderjutsuImportPreviewLayoutSummary]
    product_extras: list[OrderjutsuImportPreviewExtra]
    stock_candidates: list[OrderjutsuImportPreviewStockCandidate]
    vouchers: list[OrderjutsuImportPreviewVoucher]
    has_ingredients: bool
    ingredients_enabled: bool
    will_enable_ingredients: bool
    ingredient_matches: list[OrderjutsuImportPreviewIngredient]
    recipe_rows: list[OrderjutsuImportPreviewRecipeRow]
    has_vouchers: bool
    has_cash_registers: bool
    warnings: list[OrderjutsuImportPreviewWarning] = Field(default_factory=list)


class OrderjutsuImportCommitEvent(BaseModel):
    name: str = Field(..., min_length=1)
    start: datetime
    end: datetime
    cash_registers_enabled: bool | None = None
    vouchers_enabled: bool | None = None


class OrderjutsuImportCommitArticle(BaseModel):
    ref: int
    action: Literal["link_existing", "create_new", "skip"]
    article_id: int | None = None


class OrderjutsuImportCommitIngredient(BaseModel):
    ref: int
    action: Literal["link_existing", "create_new"]
    ingredient_id: int | None = None


class OrderjutsuImportCommitCashier(BaseModel):
    index: int
    action: Literal["link_existing", "create_org_waiter", "event_only", "skip"]
    waiter_id: int | None = None


class OrderjutsuImportCommitStation(BaseModel):
    index: int
    printer_appliance_id: int | None = None


class OrderjutsuImportCommitStockArticle(BaseModel):
    ref: int
    monitor_stock: bool | None = None
    initial_in_stock: int | None = None
    in_stock: int | None = None


class OrderjutsuImportCommitStockIngredient(BaseModel):
    ref: int
    monitor_stock: bool | None = None
    initial_in_stock: float | None = None
    in_stock: float | None = None


class OrderjutsuImportCommit(BaseModel):
    organisation_id: int
    payload: dict[str, Any]
    event: OrderjutsuImportCommitEvent
    articles: list[OrderjutsuImportCommitArticle] = Field(default_factory=list)
    ingredients: list[OrderjutsuImportCommitIngredient] = Field(default_factory=list)
    cashiers: list[OrderjutsuImportCommitCashier] = Field(default_factory=list)
    default_article_category_id: int
    enable_ingredients: bool = False
    stations: list[OrderjutsuImportCommitStation] = Field(default_factory=list)
    import_stock: bool = True
    stock_articles: list[OrderjutsuImportCommitStockArticle] = Field(default_factory=list)
    stock_ingredients: list[OrderjutsuImportCommitStockIngredient] = Field(default_factory=list)
    import_vouchers: bool = True


class OrderjutsuImportCommitResult(BaseModel):
    event_id: int
    event: EventRead
    configuration: EventConfigurationRead
