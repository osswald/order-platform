"""Cash shift sessions (Kellner-/Kassenabrechnung)."""

import json

import app.database as database
import pytest
from app.database import Base, init_test_schema
from app.domain.cash_sessions import (
    close_session,
    open_session,
    record_payments_on_session,
    session_to_sync_payload,
)
from app.models import CashSession, SyncedBundle
from app.print_worker import build_shift_close_receipt_text
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
            "cash_registers": [{"uuid": "reg-1", "name": "Kasse 1", "pin": "0000"}],
        },
    }
    db.add(SyncedBundle(id=1, json_body=json.dumps({"events": [ev]})))
    db.commit()
    yield db, ev
    db.close()


def test_waiter_shift_wallet_and_close(db_session):
    db, ev = db_session
    session = open_session(
        db,
        ev,
        event_id=1,
        subject_type="waiter",
        opening_balance_cents=5000,
        waiter_uuid="w-1",
    )
    record_payments_on_session(
        db,
        session,
        [{"type": "cash", "amount_cents": 1000}, {"type": "twint", "amount_cents": 500}],
    )
    assert session.wallet_cents == 6000
    assert session.total_cash_cents == 1000
    assert session.total_non_cash_cents == 500
    close_session(db, session, counted_cash_cents=5900)
    assert session.variance_cents == -100


def test_waiter_sequential_shifts_distinct_uuid_and_reject_double_open(db_session):
    db, ev = db_session
    first = open_session(
        db,
        ev,
        event_id=1,
        subject_type="waiter",
        opening_balance_cents=1000,
        waiter_uuid="w-1",
    )
    assert first.cash_session_uuid
    with pytest.raises(HTTPException) as exc:
        open_session(
            db,
            ev,
            event_id=1,
            subject_type="waiter",
            opening_balance_cents=0,
            waiter_uuid="w-1",
        )
    assert exc.value.status_code == 409
    close_session(db, first, counted_cash_cents=1000)
    second = open_session(
        db,
        ev,
        event_id=1,
        subject_type="waiter",
        opening_balance_cents=500,
        waiter_uuid="w-1",
    )
    assert second.cash_session_uuid
    assert second.cash_session_uuid != first.cash_session_uuid
    rows = db.query(CashSession).filter(CashSession.event_id == 1, CashSession.waiter_uuid == "w-1").all()
    assert len(rows) == 2
    assert {r.cash_session_uuid for r in rows} == {first.cash_session_uuid, second.cash_session_uuid}


def test_register_shift_uuid_in_open_and_sync_payload(db_session):
    db, ev = db_session
    session = open_session(
        db,
        ev,
        event_id=1,
        subject_type="cash_register",
        opening_balance_cents=2000,
        cash_register_uuid="reg-1",
    )
    assert session.cash_session_uuid
    payload = session_to_sync_payload(db, session)
    assert payload["cash_session_uuid"] == session.cash_session_uuid
    assert payload["subject_key"] == "cash_register:reg-1"


def test_shift_receipt_text(db_session):
    db, ev = db_session
    session = open_session(
        db,
        ev,
        event_id=1,
        subject_type="waiter",
        opening_balance_cents=5000,
        waiter_uuid="w-1",
    )
    record_payments_on_session(db, session, [{"type": "cash", "amount_cents": 1000}])
    close_session(db, session, counted_cash_cents=6000)

    payload = session_to_sync_payload(db, session)
    raw = build_shift_close_receipt_text(payload, "Fest", currency="CHF", event=ev)
    assert b"Schichtabrechnung" in raw
    assert b"Anna" in raw
    assert b"Startbetrag" in raw
    assert b"Bar-Einnahme" in raw


def test_shift_api_open_close(client_session):
    c, Session = client_session
    db = Session()
    try:
        bundle = {
            "organisation_id": 1,
            "events": [
                {
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
            ],
        }
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()
    opened = c.post(
        "/v1/shift-session/open",
        json={
            "event_id": 1,
            "subject_type": "waiter",
            "waiter_uuid": "w-1",
            "opening_balance_cents": 2000,
        },
    )
    assert opened.status_code == 200, opened.text
    sid = opened.json()["id"]
    closed = c.post(
        f"/v1/shift-session/{sid}/close",
        json={"counted_cash_cents": 2000},
    )
    assert closed.status_code == 200, closed.text
    receipt = c.post(f"/v1/shift-session/{sid}/receipt", json={})
    assert receipt.status_code == 200, receipt.text
    assert receipt.json().get("escpos_payload")
