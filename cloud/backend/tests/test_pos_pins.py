"""POS PIN hashing and edge bundle exposure."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, apply_schema_patches
from app.models import Event, EventCashRegister, EventWaiter, HireCompany, Organisation, Waiter
from app.pos_pins import apply_pos_pin_value, hash_pos_pin, is_pin_hash, verify_pos_pin
from app.routers.events import configuration_dict_for_edge, serialize_event_configuration


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    Session = sessionmaker(bind=engine)
    db = Session()
    now = datetime.now(timezone.utc)
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, name="Org", country="CH", hire_company_id=1)
    db.add(org)
    db.commit()
    yield db
    db.close()


def test_hash_and_verify_pos_pin():
    hashed = hash_pos_pin("4242")
    assert is_pin_hash(hashed)
    assert verify_pos_pin("4242", hashed)
    assert not verify_pos_pin("0000", hashed)


def test_apply_pos_pin_value_hashes_plaintext(db_session):
    waiter = Waiter(name="W", pin="", organisation_id=1)
    apply_pos_pin_value(waiter, "1111")
    assert is_pin_hash(waiter.pin)
    assert verify_pos_pin("1111", waiter.pin)


def test_edge_bundle_uses_pin_hash_not_plaintext(db_session):
    now = datetime.now(timezone.utc)
    event = Event(
        name="E",
        status="config",
        start=now,
        end=now,
        currency="CHF",
        organisation_id=1,
    )
    db_session.add(event)
    db_session.flush()
    ew = EventWaiter(event_id=event.id, uuid="ew-1", name="Anna", pin=hash_pos_pin("1234"))
    reg = EventCashRegister(
        event_id=event.id,
        uuid="reg-1",
        name="K1",
        pickup_code_prefix="A",
        pin=hash_pos_pin("0000"),
        layout_uuid="lo-1",
    )
    db_session.add_all([ew, reg])
    db_session.commit()
    db_session.refresh(event)

    cfg = serialize_event_configuration(db_session, event)
    assert cfg.event_waiters[0].has_pin is True
    assert "pin" not in cfg.event_waiters[0].model_dump()

    edge_cfg = configuration_dict_for_edge(event, cfg)
    assert edge_cfg["event_waiters"][0]["pin_hash"]
    assert "pin" not in edge_cfg["event_waiters"][0]
    assert edge_cfg["cash_registers"][0]["pin_hash"]
    assert verify_pos_pin("1234", edge_cfg["event_waiters"][0]["pin_hash"])
