"""Tests for tightened Pi edge and bundle schemas."""

from __future__ import annotations

import pytest
from app.schemas.edge import AccountSummaryResponse, LocalOrderCreate
from app.schemas.order_models import DiscountIn, OrderLineIn, PaymentIn
from pydantic import ValidationError
from tests.fixtures_bundles import default_bundle, kitchen_monitor_bundle
from vendiqo_shared.bundle_contract import EdgeBundleContract


def test_edge_bundle_contract_accepts_default_fixture():
    model = EdgeBundleContract.model_validate(default_bundle())
    assert model.organisation_id == 1
    assert len(model.events) == 1
    assert model.events[0].articles["10"].name == "Bier"


def test_edge_bundle_contract_accepts_kitchen_monitor_fixture():
    model = EdgeBundleContract.model_validate(kitchen_monitor_bundle())
    event = model.events[0]
    assert event.kitchen_monitors_enabled is True
    assert len(event.configuration.stations) == 2


def test_edge_bundle_contract_rejects_missing_organisation_id():
    payload = default_bundle()
    del payload["organisation_id"]
    with pytest.raises(ValidationError):
        EdgeBundleContract.model_validate(payload)


def test_local_order_create_accepts_typed_lines_and_payments():
    body = LocalOrderCreate.model_validate(
        {
            "client_order_id": "client-abc-123",
            "event_id": 1,
            "table_number": 5,
            "lines": [
                {
                    "article_id": 10,
                    "qty": 2,
                    "note": "ohne Eis",
                    "additions": [{"article_id": 20, "qty": 1}],
                    "discount": {"kind": "percent", "value": 10},
                }
            ],
            "payments": [{"type": "cash", "amount_cents": 900}],
            "order_discount": {"kind": "amount", "value": 100},
        }
    )
    assert body.lines[0].article_id == 10
    assert body.lines[0].discount == DiscountIn(kind="percent", value=10)
    assert body.payments[0] == PaymentIn(type="cash", amount_cents=900)


def test_local_order_create_rejects_invalid_discount_kind():
    with pytest.raises(ValidationError):
        LocalOrderCreate.model_validate(
            {
                "client_order_id": "client-abc-123",
                "event_id": 1,
                "lines": [{"article_id": 10, "discount": {"kind": "bogus", "value": 5}}],
            }
        )


def test_account_summary_response_accepts_typed_open_orders():
    response = AccountSummaryResponse.model_validate(
        {
            "currency": "CHF",
            "open_orders": [
                {
                    "local_order_id": 1,
                    "client_order_id": "c-1",
                    "lines": [{"article_id": 10, "qty": 1}],
                    "line_total_cents": 500,
                }
            ],
            "line_groups": [
                {
                    "article_id": 10,
                    "total_qty": 1,
                    "unit_cents": 500,
                    "line_total_cents": 500,
                }
            ],
            "total_cents": 500,
            "item_count": 1,
        }
    )
    assert response.open_orders[0].lines[0] == OrderLineIn(article_id=10, qty=1)
