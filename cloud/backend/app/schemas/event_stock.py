"""Event stock API schemas."""

from pydantic import BaseModel, Field, model_validator

from ..ingredient_stock import normalize_ingredient_stock_fields
from ..stock import normalize_stock_fields


class EventStockItemRead(BaseModel):
    id: int
    name: str
    label: str
    monitor_stock: bool
    initial_in_stock: int | None = None
    in_stock: int | None = None


class EventIngredientStockItemRead(BaseModel):
    id: int
    name: str
    unit: str | None = None
    monitor_stock: bool
    initial_in_stock: float | None = None
    in_stock: float | None = None


class EventStockListRead(BaseModel):
    ingredients: list[EventIngredientStockItemRead] = Field(default_factory=list)
    items: list[EventStockItemRead]


class EventStockItemIn(BaseModel):
    article_id: int
    monitor_stock: bool = False
    initial_in_stock: int | None = Field(None, ge=0)
    in_stock: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def normalize(self):
        monitor = self.monitor_stock
        if "initial_in_stock" in self.model_fields_set:
            monitor, qty = normalize_stock_fields(monitor, self.initial_in_stock)
            self.initial_in_stock = qty
        if "in_stock" in self.model_fields_set:
            monitor, qty = normalize_stock_fields(monitor, self.in_stock)
            self.in_stock = qty
        self.monitor_stock = monitor
        return self


class EventIngredientStockItemIn(BaseModel):
    ingredient_id: int
    monitor_stock: bool = False
    initial_in_stock: float | None = Field(None, ge=0)
    in_stock: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def normalize(self):
        monitor = self.monitor_stock
        if "initial_in_stock" in self.model_fields_set:
            monitor, qty = normalize_ingredient_stock_fields(monitor, self.initial_in_stock)
            self.initial_in_stock = float(qty) if qty is not None else None
        if "in_stock" in self.model_fields_set:
            monitor, qty = normalize_ingredient_stock_fields(monitor, self.in_stock)
            self.in_stock = float(qty) if qty is not None else None
        self.monitor_stock = monitor
        return self


class EventStockUpdateIn(BaseModel):
    ingredients: list[EventIngredientStockItemIn] = Field(default_factory=list)
    items: list[EventStockItemIn] = Field(default_factory=list)
