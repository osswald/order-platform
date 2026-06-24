"""Edge operational snapshot for Pi restore."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from tests.helpers import ensure_country
from app.edge_operational_mirror import upsert_edge_kitchen_ticket_snapshot, upsert_edge_order_snapshot
from app.edge_operational_snapshot import build_operational_snapshot_for_events
from app.event_cash_sessions import upsert_edge_cash_session
from app.models import Event, HireCompany, Organisation


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch_country_id = ensure_country(db, "CH", country_id=1)
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, hire_company_id=1, name="Org", country_id=ch_country_id, currency="CHF")
    db.add(org)
    now = datetime.now(timezone.utc)
    ev = Event(
        id=1,
        name="Fest",
        status="prod",
        start=now,
        end=now,
        organisation_id=1,
        shift_settlement_enabled=True,
    )
    db.add(ev)
    db.commit()
    yield db, ev
    db.close()


def test_order_snapshot_open_and_paid(db_session):
    db, ev = db_session
    open_payload = {
        "client_order_id": "order-open-1",
        "table_number": 5,
        "payment_status": "open",
        "lines": [{"article_id": 1, "qty": 2, "unit_cents": 500}],
    }
    upsert_edge_order_snapshot(
        db,
        organisation_id=1,
        appliance_id=10,
        event_id=1,
        payload=open_payload,
    )
    db.commit()

    snapshot = build_operational_snapshot_for_events(db, organisation_id=1, events=[ev])
    assert len(snapshot["events"]) == 1
    assert snapshot["events"][0]["open_orders"][0]["client_order_id"] == "order-open-1"

    paid_payload = {**open_payload, "payment_status": "paid", "lines": []}
    upsert_edge_order_snapshot(
        db,
        organisation_id=1,
        appliance_id=10,
        event_id=1,
        payload=paid_payload,
    )
    db.commit()
    snapshot2 = build_operational_snapshot_for_events(db, organisation_id=1, events=[ev])
    assert snapshot2["events"] == []


def test_kitchen_snapshot_included_for_open_order(db_session):
    db, ev = db_session
    upsert_edge_order_snapshot(
        db,
        organisation_id=1,
        appliance_id=10,
        event_id=1,
        payload={
            "client_order_id": "order-k-1",
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1}],
        },
    )
    upsert_edge_kitchen_ticket_snapshot(
        db,
        organisation_id=1,
        appliance_id=10,
        event_id=1,
        payload={
            "client_order_id": "order-k-1",
            "tickets": [
                {
                    "station_uuid": "st-1",
                    "printer_appliance_id": 5,
                    "status": "partial",
                    "lines": [{"line_index": 0, "line_payload": {"article_id": 1}, "qty_total": 2, "qty_printed": 1}],
                }
            ],
        },
    )
    db.commit()
    snapshot = build_operational_snapshot_for_events(db, organisation_id=1, events=[ev])
    kitchen = snapshot["events"][0]["kitchen_tickets"]
    assert kitchen[0]["client_order_id"] == "order-k-1"
    assert kitchen[0]["tickets"][0]["status"] == "partial"


def test_cash_session_org_scoped_by_subject_key(db_session):
    db, ev = db_session
    payload = {
        "cash_session_id": 7,
        "subject_type": "waiter",
        "waiter_uuid": "w-1",
        "subject_name": "Anna",
        "status": "OPEN",
        "opening_balance_cents": 0,
        "wallet_cents": 100,
        "total_cash_cents": 100,
        "total_non_cash_cents": 0,
        "ledger": [],
    }
    upsert_edge_cash_session(db, organisation_id=1, appliance_id=10, event_id=1, payload=payload)
    payload["cash_session_id"] = 99
    payload["wallet_cents"] = 200
    upsert_edge_cash_session(db, organisation_id=1, appliance_id=11, event_id=1, payload=payload)
    db.commit()

    snapshot = build_operational_snapshot_for_events(db, organisation_id=1, events=[ev])
    sessions = snapshot["events"][0]["open_cash_sessions"]
    assert len(sessions) == 1
    assert sessions[0]["payload"]["wallet_cents"] == 200
