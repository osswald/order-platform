"""Verify pull + reapply keeps stock deductions for unsent outbox orders."""

import json

from app.models import OutboxEntry, SyncedBundle
from app.stock import apply_stock_to_bundle
from app.sync_service import reapply_pending_stock


def _bundle_with_stock(qty: int = 10) -> dict:
    return {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "articles": {
                    "42": {
                        "id": 42,
                        "name": "Beer",
                        "monitor_stock": True,
                        "in_stock": qty,
                        "sellable": qty > 0,
                    }
                },
            }
        ],
    }


def test_reapply_pending_stock_after_cloud_pull(db_session):
    bundle = _bundle_with_stock(10)
    db_session.add(
        SyncedBundle(
            id=1,
            json_body=json.dumps(bundle),
        )
    )
    db_session.add(
        OutboxEntry(
            client_order_id="test-order-1",
            event_id=1,
            payload_json=json.dumps(
                {
                    "event_id": 1,
                    "lines": [{"article_id": 42, "qty": 3}],
                }
            ),
            status="pending",
        )
    )
    db_session.commit()

    cloud_bundle = _bundle_with_stock(10)
    reapply_pending_stock(db_session, cloud_bundle)

    arts = cloud_bundle["events"][0]["articles"]
    assert arts["42"]["in_stock"] == 7
    assert arts["42"]["sellable"] is True

    fresh = _bundle_with_stock(10)
    apply_stock_to_bundle(fresh, 1, [{"article_id": 42, "qty": 3}])
    assert fresh["events"][0]["articles"]["42"]["in_stock"] == 7
