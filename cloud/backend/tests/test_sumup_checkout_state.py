"""Unit tests for Solo/online SumUp checkout payload helpers."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.sumup_checkout_state import (
    apply_checkout_payload,
    normalize_checkout_status,
    transaction_id_from_checkout,
    unwrap_sumup_data,
)


def test_normalize_checkout_status_maps_reader_and_online_values():
    assert normalize_checkout_status("PENDING") == "pending"
    assert normalize_checkout_status("successful") == "paid"
    assert normalize_checkout_status("PAID") == "paid"
    assert normalize_checkout_status("failed") == "failed"
    assert normalize_checkout_status("cancelled") == "terminated"


def test_unwrap_sumup_data_flattens_reader_envelope():
    payload = {
        "data": {
            "checkout_id": "co_1",
            "client_transaction_id": "ctx_1",
            "status": "pending",
        }
    }
    unwrapped = unwrap_sumup_data(payload)
    assert unwrapped["checkout_id"] == "co_1"
    assert unwrapped["client_transaction_id"] == "ctx_1"
    assert unwrapped["status"] == "pending"


def test_transaction_id_prefers_client_transaction_id_for_reader():
    assert (
        transaction_id_from_checkout(
            {"client_transaction_id": "ctx_solo", "transactions": [{"id": "online_txn"}]}
        )
        == "ctx_solo"
    )
    assert transaction_id_from_checkout({"transactions": [{"id": "online_txn"}]}) == "online_txn"


def test_apply_checkout_payload_handles_nested_reader_success():
    row = SimpleNamespace(status="pending", sumup_transaction_id=None)
    apply_checkout_payload(
        row,
        {
            "data": {
                "checkout_id": "co_1",
                "client_transaction_id": "ctx_1",
                "status": "successful",
            }
        },
    )
    assert row.status == "paid"
    assert row.sumup_transaction_id == "ctx_1"


def test_apply_checkout_payload_uses_payment_status_when_status_pending():
    row = SimpleNamespace(status="pending", sumup_transaction_id=None)
    apply_checkout_payload(
        row,
        {
            "data": {
                "checkout_id": "co_1",
                "client_transaction_id": "ctx_1",
                "status": "pending",
                "payment_status": "failed",
                "payment_failure_reason": "declined",
            }
        },
    )
    assert row.status == "failed"


def test_apply_checkout_payload_expires_stale_pending_checkout():
    row = SimpleNamespace(status="pending", sumup_transaction_id=None)
    past = (datetime.now(UTC) - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
    apply_checkout_payload(
        row,
        {
            "data": {
                "checkout_id": "co_stale",
                "client_transaction_id": "ctx_stale",
                "status": "pending",
                "payment_status": None,
                "valid_until": past,
            }
        },
    )
    assert row.status == "terminated"
