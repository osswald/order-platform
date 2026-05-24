"""Verify pull + reapply keeps stock deductions for unsent outbox orders."""

import json

from app.stock import apply_stock_to_bundle
from app.sync_service import reapply_pending_stock
from app.models import OutboxEntry, SyncedBundle
from app.database import Base, SessionLocal, engine


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


def test_reapply_pending_stock_after_cloud_pull():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bundle = _bundle_with_stock(10)
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        if row:
            row.json_body = json.dumps(bundle)
        else:
            db.add(
                SyncedBundle(
                    id=1,
                    json_body=json.dumps(bundle),
                )
            )
        payload = json.dumps(
            {
                "event_id": 1,
                "lines": [{"article_id": 42, "qty": 3}],
            }
        )
        outbox = db.query(OutboxEntry).filter(OutboxEntry.client_order_id == "test-order-1").first()
        if outbox:
            outbox.event_id = 1
            outbox.payload_json = payload
            outbox.status = "pending"
        else:
            db.add(
                OutboxEntry(
                    client_order_id="test-order-1",
                    event_id=1,
                    payload_json=payload,
                    status="pending",
                )
            )
        db.commit()

        # Simulate cloud pull restoring pre-order stock
        cloud_bundle = _bundle_with_stock(10)
        reapply_pending_stock(db, cloud_bundle)

        arts = cloud_bundle["events"][0]["articles"]
        assert arts["42"]["in_stock"] == 7
        assert arts["42"]["sellable"] is True

        # Direct deduction matches reapply
        fresh = _bundle_with_stock(10)
        apply_stock_to_bundle(fresh, 1, [{"article_id": 42, "qty": 3}])
        assert fresh["events"][0]["articles"]["42"]["in_stock"] == 7
    finally:
        db.close()
