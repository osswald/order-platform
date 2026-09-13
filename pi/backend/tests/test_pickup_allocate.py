"""Unit tests for event / per-station pickup number allocation."""

from __future__ import annotations

from app.models import EventPickupCounter
from app.routers.edge_common import _allocate_pickup_number


def test_allocate_register_mode_shares_event_wide_sequence(db_session):
    db = db_session
    assert _allocate_pickup_number(db, 1) == 1
    assert _allocate_pickup_number(db, 1) == 2
    assert _allocate_pickup_number(db, 1, station_uuid=None) == 3
    assert _allocate_pickup_number(db, 1, station_uuid="") == 4

    rows = db.query(EventPickupCounter).filter(EventPickupCounter.event_id == 1).all()
    assert len(rows) == 1
    assert rows[0].station_uuid == ""
    assert rows[0].next_number == 5


def test_allocate_station_mode_independent_sequences(db_session):
    db = db_session
    assert _allocate_pickup_number(db, 1, station_uuid="st-grill") == 1
    assert _allocate_pickup_number(db, 1, station_uuid="st-bar") == 1
    assert _allocate_pickup_number(db, 1, station_uuid="st-grill") == 2
    assert _allocate_pickup_number(db, 1, station_uuid="st-bar") == 2
    assert _allocate_pickup_number(db, 1, station_uuid="st-grill") == 3

    by_station = {
        r.station_uuid: r.next_number
        for r in db.query(EventPickupCounter).filter(EventPickupCounter.event_id == 1).all()
    }
    assert by_station == {"st-grill": 4, "st-bar": 3}


def test_allocate_event_wide_and_station_rows_do_not_collide(db_session):
    db = db_session
    assert _allocate_pickup_number(db, 1) == 1
    assert _allocate_pickup_number(db, 1, station_uuid="st-bar") == 1
    assert _allocate_pickup_number(db, 1) == 2
    assert _allocate_pickup_number(db, 1, station_uuid="st-bar") == 2

    rows = {
        (r.event_id, r.station_uuid): r.next_number
        for r in db.query(EventPickupCounter).all()
    }
    assert rows[(1, "")] == 3
    assert rows[(1, "st-bar")] == 3
