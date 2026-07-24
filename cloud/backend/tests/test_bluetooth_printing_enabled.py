"""Event flag bluetooth_printing_enabled (Pi waiter Bluetooth printing)."""

from datetime import UTC, datetime

import pytest
from app.database import Base
from app.models import Event, HireCompany, Organisation
from app.routers.edge import EdgeEventBundle
from app.routers.events import event_response
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
    now = datetime.now(UTC)
    db.add(HireCompany(id=1, name="HC"))
    db.add(Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF"))
    ev = Event(
        id=1,
        name="Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
    )
    db.add(ev)
    db.commit()
    yield db, ev
    db.close()


def test_bluetooth_printing_enabled_defaults_false(db_session):
    db, ev = db_session
    db.refresh(ev)
    assert ev.bluetooth_printing_enabled is False
    data = event_response(ev)
    assert data["bluetooth_printing_enabled"] is False


def test_bluetooth_printing_enabled_in_event_response(db_session):
    db, ev = db_session
    ev.bluetooth_printing_enabled = True
    db.commit()
    db.refresh(ev)
    assert event_response(ev)["bluetooth_printing_enabled"] is True


def test_edge_event_bundle_includes_bluetooth_printing_enabled(db_session):
    db, ev = db_session
    ev.bluetooth_printing_enabled = True
    db.commit()
    db.refresh(ev)
    bundle = EdgeEventBundle(
        id=ev.id,
        name=ev.name,
        status=ev.status,
        currency="CHF",
        payment_mode="pay_later",
        payment_types=["cash"],
        shift_settlement_enabled=False,
        discounts_enabled=False,
        offer_payment_receipt=False,
        bluetooth_printing_enabled=bool(getattr(ev, "bluetooth_printing_enabled", False)),
        twint_qr_data_url=None,
        start=ev.start,
        end=ev.end,
        configuration={},
        articles={},
    )
    assert bundle.bluetooth_printing_enabled is True
