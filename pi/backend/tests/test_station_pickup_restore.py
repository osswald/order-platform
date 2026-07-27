"""Operational restore recreates station pickups from order payload."""

from __future__ import annotations

import json

import pytest
from app.models import LocalOrder, StationPickup, SyncedBundle
from app.operational_restore import restore_operational_snapshot
from tests.fixtures_bundles import bundle_copy, cash_register_bundle


@pytest.fixture
def bundle():
    return bundle_copy(cash_register_bundle())


def test_restore_recreates_station_pickups(isolated_engine, db_session, bundle):
    db = db_session
    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()

    snapshot = {
        "organisation_id": 1,
        "events": [
            {
                "event_id": 1,
                "open_orders": [
                    {
                        "client_order_id": "reg-restore-1",
                        "payload": {
                            "client_order_id": "reg-restore-1",
                            "event_id": 1,
                            "order_source": "cash_register",
                            "cash_register_uuid": "reg-1",
                            "payment_status": "open",
                            "table_number": 0,
                            "pickup_code": "A1",
                            "pickup_codes": ["A1", "A2"],
                            "pickup_status": "pending",
                            "pickup_number": 2,
                            "lines": [
                                {"article_id": 10, "qty": 1, "note": "", "additions": []},
                                {"article_id": 20, "qty": 1, "note": "", "additions": []},
                            ],
                            "pickups": [
                                {
                                    "station_uuid": "st-kitchen",
                                    "pickup_code": "A1",
                                    "pickup_status": "pending",
                                },
                                {
                                    "station_uuid": "st-bar",
                                    "pickup_code": "A2",
                                    "pickup_status": "ready",
                                    "ready_at": "2026-07-27T12:00:00+00:00",
                                },
                            ],
                        },
                    }
                ],
                "kitchen_tickets": [],
                "cash_sessions": [],
            }
        ],
    }
    restore_operational_snapshot(db, snapshot, bundle)
    db.commit()

    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == "reg-restore-1").one()
    pickups = (
        db.query(StationPickup)
        .filter(StationPickup.local_order_id == order.id)
        .order_by(StationPickup.id.asc())
        .all()
    )
    assert [(p.station_uuid, p.pickup_code, p.pickup_status) for p in pickups] == [
        ("st-kitchen", "A1", "pending"),
        ("st-bar", "A2", "ready"),
    ]
