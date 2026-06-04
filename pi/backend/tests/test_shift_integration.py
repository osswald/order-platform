"""Cash shift integration wiring."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as database
from app.database import Base, init_test_schema
from app.domain.cash_sessions import open_session
from app.models import SyncedBundle
from app.shift_integration import attach_shift_to_payload, record_shift_order_submit, session_to_api_dict


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine)
    Base.metadata.drop_all(bind=engine)
    init_test_schema()
    Session = sessionmaker(bind=engine)
    db = Session()
    ev = {
        "id": 1,
        "name": "Fest",
        "currency": "CHF",
        "shift_settlement_enabled": True,
        "configuration": {
            "event_waiters": [{"uuid": "w-1", "name": "Anna", "pin": "1"}],
            "cash_registers": [],
            "stations": [],
        },
    }
    db.add(SyncedBundle(id=1, json_body=json.dumps({"events": [ev]})))
    db.commit()
    yield db, ev
    db.close()


def test_session_to_api_dict_and_attach_shift(db_session):
    db, ev = db_session
    session = open_session(
        db,
        ev,
        event_id=1,
        subject_type="waiter",
        opening_balance_cents=1000,
        waiter_uuid="w-1",
    )
    db.commit()
    api = session_to_api_dict(session)
    assert api["status"] == "OPEN"
    assert api["subject_name"] == "Anna"

    payload = {}
    attached = attach_shift_to_payload(
        db,
        ev,
        payload,
        event_id=1,
        waiter_uuid="w-1",
        cash_register_uuid=None,
    )
    assert attached is not None
    assert payload["cash_session_id"] == int(session.id)


def test_record_shift_order_submit_updates_wallet(db_session):
    db, ev = db_session
    open_session(
        db,
        ev,
        event_id=1,
        subject_type="waiter",
        opening_balance_cents=0,
        waiter_uuid="w-1",
    )
    db.commit()
    record_shift_order_submit(
        db,
        ev,
        event_id=1,
        waiter_uuid="w-1",
        cash_register_uuid=None,
        amount_cents=1500,
        reference_id="ord-1",
    )
    db.commit()
    from app.models_operational import CashSessionLedger

    rows = (
        db.query(CashSessionLedger)
        .filter(CashSessionLedger.entry_type == "order")
        .all()
    )
    assert len(rows) >= 1
    assert int(rows[0].amount_cents) == 1500
