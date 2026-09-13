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


def test_restore_bumps_event_wide_pickup_counter_in_register_mode(isolated_engine, db_session, bundle):
    from app.models import EventPickupCounter

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
                        "client_order_id": "reg-restore-counters",
                        "payload": {
                            "client_order_id": "reg-restore-counters",
                            "event_id": 1,
                            "order_source": "cash_register",
                            "cash_register_uuid": "reg-1",
                            "payment_status": "open",
                            "table_number": 0,
                            "pickup_code": "A5",
                            "pickup_codes": ["A5", "A7"],
                            "pickup_status": "pending",
                            "pickup_number": 7,
                            "lines": [{"article_id": 20, "qty": 1, "note": "", "additions": []}],
                            "pickups": [
                                {
                                    "station_uuid": "st-bar",
                                    "pickup_code": "A7",
                                    "pickup_status": "pending",
                                }
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

    row = (
        db.query(EventPickupCounter)
        .filter(EventPickupCounter.event_id == 1, EventPickupCounter.station_uuid == "")
        .one()
    )
    assert row.next_number == 8


def test_restore_bumps_per_station_counters_in_station_mode(isolated_engine, db_session):
    from app.models import EventPickupCounter
    from tests.fixtures_bundles import station_prefix_mode_bundle

    bundle = bundle_copy(station_prefix_mode_bundle())
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
                        "client_order_id": "reg-restore-station",
                        "payload": {
                            "client_order_id": "reg-restore-station",
                            "event_id": 1,
                            "order_source": "cash_register",
                            "cash_register_uuid": "reg-1",
                            "payment_status": "open",
                            "table_number": 0,
                            "pickup_code": "G3",
                            "pickup_codes": ["G3", "B5"],
                            "pickup_status": "pending",
                            "lines": [
                                {"article_id": 10, "qty": 1, "note": "", "additions": []},
                                {"article_id": 20, "qty": 1, "note": "", "additions": []},
                            ],
                            "pickups": [
                                {
                                    "station_uuid": "st-kitchen",
                                    "pickup_code": "G3",
                                    "pickup_status": "pending",
                                },
                                {
                                    "station_uuid": "st-bar",
                                    "pickup_code": "B5",
                                    "pickup_status": "ready",
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

    counters = {
        r.station_uuid: r.next_number
        for r in db.query(EventPickupCounter).filter(EventPickupCounter.event_id == 1).all()
    }
    assert counters == {"st-kitchen": 4, "st-bar": 6}
    assert "" not in counters

