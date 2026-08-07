"""HTTP API for Pi admin load-test (Lasttest)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..load_test_job import get_status, start_load_test, stop_load_test

router = APIRouter()


class LoadTestStartBody(BaseModel):
    event_id: int
    waiter_count: int = Field(0, ge=0, le=100)
    cash_register_count: int = Field(0, ge=0, le=100)
    table_min: int = Field(1, ge=1, le=99999)
    table_max: int = Field(40, ge=1, le=99999)
    total_orders: int = Field(..., ge=1, le=10000)
    # Test/ops override; production UI omits this (defaults to 60s)
    burst_interval_seconds: float = Field(60.0, ge=0.05, le=600.0)
    rng_seed: int | None = None


class LoadTestStatusResponse(BaseModel):
    state: Literal["idle", "running", "stopping", "done", "failed"]
    event_id: int | None = None
    config: dict[str, Any] | None = None
    placed: int = 0
    failed: int = 0
    receipts_printed: int = 0
    current_burst: int = 0
    total_bursts: int = 0
    last_error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


@router.get("/v1/load-test/status", response_model=LoadTestStatusResponse)
def load_test_status() -> LoadTestStatusResponse:
    return LoadTestStatusResponse.model_validate(get_status())


@router.post("/v1/load-test/start", response_model=LoadTestStatusResponse)
def load_test_start(body: LoadTestStartBody) -> LoadTestStatusResponse:
    status = start_load_test(
        event_id=body.event_id,
        waiter_count=body.waiter_count,
        cash_register_count=body.cash_register_count,
        table_min=body.table_min,
        table_max=body.table_max,
        total_orders=body.total_orders,
        burst_interval_seconds=body.burst_interval_seconds,
        rng_seed=body.rng_seed,
    )
    return LoadTestStatusResponse.model_validate(status)


@router.post("/v1/load-test/stop", response_model=LoadTestStatusResponse)
def load_test_stop() -> LoadTestStatusResponse:
    status = stop_load_test()
    return LoadTestStatusResponse.model_validate(status)
