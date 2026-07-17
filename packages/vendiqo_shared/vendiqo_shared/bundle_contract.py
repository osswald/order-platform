"""Top-level keys in the edge organisation bundle exchanged between cloud and pi."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

BUNDLE_TOP_LEVEL_KEYS = frozenset(
    {
        "organisation_id",
        "events",
        "position_comments_enabled",
        "position_comment_presets",
        "ingredients_enabled",
        "admin_pin_hashes",
    }
)


class EdgeBundleArticleAddition(BaseModel):
    model_config = ConfigDict(extra="allow")

    article_id: int
    name: str | None = None
    label: str | None = None
    price: float | None = None
    in_stock: int | None = None
    sellable: bool | None = None
    monitor_stock: bool | None = None
    preselected: bool | None = None


class EdgeBundleArticleIngredient(BaseModel):
    model_config = ConfigDict(extra="allow")

    ingredient_id: int
    name: str | None = None
    unit: str | None = None
    amount: float | None = None
    sort_order: int | None = None


class EdgeBundleIngredient(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    unit: str | None = None
    in_stock: float | None = None
    sellable: bool | None = None
    monitor_stock: bool | None = None


class EdgeBundleArticle(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    price: float
    additions: list[EdgeBundleArticleAddition] = Field(default_factory=list)
    ingredients: list[EdgeBundleArticleIngredient] = Field(default_factory=list)
    label: str | None = None
    in_stock: int | None = None
    sellable: bool | None = None
    monitor_stock: bool | None = None


class EdgeStationConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    uuid: str
    name: str
    sort_order: int = 0
    article_ids: list[int] = Field(default_factory=list)
    printer_appliance_id: int | None = None


class EdgeEventConfiguration(BaseModel):
    model_config = ConfigDict(extra="allow")

    stations: list[EdgeStationConfig] = Field(default_factory=list)
    event_waiters: list[dict[str, Any]] = Field(default_factory=list)
    waiters: list[dict[str, Any]] = Field(default_factory=list)
    cash_registers: list[dict[str, Any]] = Field(default_factory=list)
    kitchen_monitors: list[dict[str, Any]] = Field(default_factory=list)
    voucher_definitions: list[dict[str, Any]] = Field(default_factory=list)
    app_layouts: list[dict[str, Any]] = Field(default_factory=list)


class EdgeBundleEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    currency: str = "EUR"
    payment_mode: str = "pay_later"
    payment_types: list[str] = Field(default_factory=list)
    articles: dict[str, EdgeBundleArticle] = Field(default_factory=dict)
    ingredients: dict[str, EdgeBundleIngredient] = Field(default_factory=dict)
    configuration: EdgeEventConfiguration = Field(default_factory=EdgeEventConfiguration)
    kitchen_monitors_enabled: bool | None = None
    printer_hosts: dict[str, Any] | None = None
    discounts_enabled: bool | None = None
    twint_qr_data_url: str | None = None


class PositionCommentPreset(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    text: str


class EdgeBundleContract(BaseModel):
    """Validated shape for synced organisation bundles."""

    model_config = ConfigDict(extra="allow")

    organisation_id: int
    events: list[EdgeBundleEvent] = Field(default_factory=list)
    position_comments_enabled: bool = False
    position_comment_presets: list[PositionCommentPreset] = Field(default_factory=list)
    ingredients_enabled: bool = False
    admin_pin_hashes: list[str] = Field(default_factory=list)
