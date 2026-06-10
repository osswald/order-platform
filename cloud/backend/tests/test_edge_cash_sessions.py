"""Edge cash session ingest and list API."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.event_cash_sessions import build_cash_sessions_page, upsert_edge_cash_session
from app.models import EdgeCashSession, Event, HireCompany, Organisation


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, hire_company_id=1, name="Org", country="CH", currency="CHF")
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


def test_upsert_and_list_cash_sessions(db_session):
    db, event = db_session
    payload = {
        "cash_session_id": 42,
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
    page = build_cash_sessions_page(db, event)
    assert page["total"] == 1
    assert page["items"][0]["subject_name"] == "Anna"
