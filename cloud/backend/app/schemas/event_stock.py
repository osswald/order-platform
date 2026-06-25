"""Event stock API schemas."""


from pydantic import BaseModel, Field, model_validator

from ..stock import normalize_stock_fields


class EventStockItemRead(BaseModel):
    id: int
    name: str
    label: str
    monitor_stock: bool
    in_stock: int | None = None


class EventStockListRead(BaseModel):
    items: list[EventStockItemRead]


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
    items: list[EventStockItemIn] = Field(default_factory=list)
