"""Cash shift sessions (Kellner-/Kassenabrechnung)."""

import base64
import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.cash_sessions import close_session, open_session, record_payments_on_session
from app.models import SyncedBundle
from app.print_worker import build_shift_close_receipt_text, _escpos_text


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
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
    from app.domain.cash_sessions import session_to_sync_payload

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
