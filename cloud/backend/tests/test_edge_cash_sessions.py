"""Edge cash session ingest and list API."""

from datetime import UTC, datetime

import pytest
from app.database import Base
from app.event_cash_sessions import build_cash_sessions_page, upsert_edge_cash_session
from app.models import EdgeCashSession, Event, HireCompany, Organisation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


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
    now = datetime.now(UTC)
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


def test_upsert_and_list_cash_sessions(db_session):
    db, event = db_session
    payload = {
        "cash_session_id": 42,
        "cash_session_uuid": "11111111-1111-1111-1111-111111111111",
        "subject_type": "waiter",
        "waiter_uuid": "w-1",
        "subject_name": "Anna",
        "status": "CLOSED",
        "opening_balance_cents": 5000,
        "wallet_cents": 6000,
        "total_cash_cents": 1000,
        "total_non_cash_cents": 0,
        "counted_cash_cents": 6000,
        "variance_cents": 0,
        "started_at": "2026-06-01T10:00:00+00:00",
        "ended_at": "2026-06-01T18:00:00+00:00",
        "payments_by_method": {"cash": 1000},
        "ledger": [],
    }
    upsert_edge_cash_session(
        db,
        organisation_id=1,
        appliance_id=1,
        event_id=1,
        payload=payload,
    )
    db.commit()
    row = db.query(EdgeCashSession).one()
    assert row.cash_session_id == 42
    assert row.cash_session_uuid == "11111111-1111-1111-1111-111111111111"
    assert row.subject_key == "waiter:w-1"
    page = build_cash_sessions_page(db, event)
    assert page["total"] == 1
    assert page["items"][0]["subject_name"] == "Anna"
    assert page["items"][0]["cash_session_uuid"] == "11111111-1111-1111-1111-111111111111"


def test_two_closed_waiter_shifts_both_persist(db_session):
    db, event = db_session
    base = {
        "subject_type": "waiter",
        "waiter_uuid": "w-1",
        "subject_name": "Anna",
        "status": "CLOSED",
        "opening_balance_cents": 0,
        "wallet_cents": 100,
        "total_cash_cents": 100,
        "total_non_cash_cents": 0,
        "counted_cash_cents": 100,
        "variance_cents": 0,
        "payments_by_method": {},
        "ledger": [],
    }
    upsert_edge_cash_session(
        db,
        organisation_id=1,
        appliance_id=1,
        event_id=1,
        payload={
            **base,
            "cash_session_id": 1,
            "cash_session_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "started_at": "2026-06-01T10:00:00+00:00",
            "ended_at": "2026-06-01T14:00:00+00:00",
        },
    )
    upsert_edge_cash_session(
        db,
        organisation_id=1,
        appliance_id=1,
        event_id=1,
        payload={
            **base,
            "cash_session_id": 2,
            "cash_session_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "started_at": "2026-06-01T15:00:00+00:00",
            "ended_at": "2026-06-01T20:00:00+00:00",
        },
    )
    db.commit()
    assert db.query(EdgeCashSession).count() == 2
    page = build_cash_sessions_page(db, event)
    assert page["total"] == 2
    uuids = {item["cash_session_uuid"] for item in page["items"]}
    assert uuids == {
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    }


def test_resync_same_uuid_updates_one_row(db_session):
    db, event = db_session
    uuid_val = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    open_payload = {
        "cash_session_id": 5,
        "cash_session_uuid": uuid_val,
        "subject_type": "waiter",
        "waiter_uuid": "w-1",
        "subject_name": "Anna",
        "status": "OPEN",
        "opening_balance_cents": 500,
        "wallet_cents": 500,
        "total_cash_cents": 0,
        "total_non_cash_cents": 0,
        "started_at": "2026-06-01T10:00:00+00:00",
        "ledger": [],
    }
    upsert_edge_cash_session(db, organisation_id=1, appliance_id=1, event_id=1, payload=open_payload)
    db.commit()
    closed_payload = {
        **open_payload,
        "status": "CLOSED",
        "wallet_cents": 1500,
        "total_cash_cents": 1000,
        "counted_cash_cents": 1500,
        "variance_cents": 0,
        "ended_at": "2026-06-01T18:00:00+00:00",
    }
    upsert_edge_cash_session(db, organisation_id=1, appliance_id=1, event_id=1, payload=closed_payload)
    db.commit()
    rows = db.query(EdgeCashSession).all()
    assert len(rows) == 1
    assert rows[0].status == "CLOSED"
    assert rows[0].wallet_cents == 1500
    assert rows[0].cash_session_uuid == uuid_val
    page = build_cash_sessions_page(db, event)
    assert page["total"] == 1
    assert page["items"][0]["status"] == "CLOSED"


def test_upsert_without_uuid_is_noop(db_session):
    db, _event = db_session
    upsert_edge_cash_session(
        db,
        organisation_id=1,
        appliance_id=1,
        event_id=1,
        payload={
            "cash_session_id": 1,
            "subject_type": "waiter",
            "waiter_uuid": "w-1",
            "status": "OPEN",
            "opening_balance_cents": 0,
            "wallet_cents": 0,
            "total_cash_cents": 0,
            "total_non_cash_cents": 0,
        },
    )
    db.commit()
    assert db.query(EdgeCashSession).count() == 0
