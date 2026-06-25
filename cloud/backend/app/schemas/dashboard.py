"""Dashboard and onboarding response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingTaskRead(BaseModel):
    id: str
    group: str
    done: bool
    done_manually: bool = False
    visible: bool = True
    target_route: str | None = None
    target_params: dict[str, str] | None = None
    target_query: dict[str, str] | None = None
    target_event_id: int | None = None


class OnboardingRead(BaseModel):
    dismissed: bool
    tasks: list[OnboardingTaskRead] = Field(default_factory=list)


class DashboardCatalogRead(BaseModel):
    waiters: int
    articles: int
    categories: int


class DashboardLendingsRead(BaseModel):
    current: int
    planned: int


class DashboardAttentionItemRead(BaseModel):
    type: str
    event_id: int
    event_name: str


class DashboardSalesTotalsRead(BaseModel):
    distinct_orders_count: int
    line_cents: int
    paid_cents: int
    open_cents: int


class DashboardSalesEventRowRead(BaseModel):
    event_id: int
    name: str
    status: str
    start: str | None = None
    end: str | None = None
    distinct_orders_count: int
    line_cents: int
    paid_cents: int
    open_cents: int


class DashboardSalesRead(BaseModel):
    currency: str
    totals: DashboardSalesTotalsRead
    by_event: list[DashboardSalesEventRowRead]


class DashboardSummaryRead(BaseModel):
    organisation_id: int
    organisation_name: str
    events_by_status: dict[str, int]
    running_event_ids: list[int]
    running_events_count: int
    events_total: int
    catalog: DashboardCatalogRead
    lendings: DashboardLendingsRead
    attention: list[DashboardAttentionItemRead]
    sales: DashboardSalesRead
    onboarding: OnboardingRead
