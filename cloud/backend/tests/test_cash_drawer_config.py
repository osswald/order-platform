"""Cash register cash drawer command configuration."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.database import Base
from app.event_config_validation import assert_cash_registers_valid, replace_event_configuration
from app.models import Event, EventAppLayout, EventCashRegister, HireCompany, Organisation
from fastapi import HTTPException
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
    org = Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF")
    db.add(org)
    now = datetime.now(UTC)
    ev = Event(
        id=1,
        name="Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
        cash_registers_enabled=True,
    )
    db.add(ev)
    layout = EventAppLayout(
        id=1,
        event_id=1,
        uuid="layout-1",
        name="Kasse",
        is_default=True,
        grid_width=1,
        grid_height=1,
    )
    db.add(layout)
    db.commit()
    yield db, ev, layout
    db.close()


def _register(layout_uuid: str, **kwargs):
    defaults = {
        "name": "Hauptkasse",
        "pickup_code_prefix": "A",
        "pin": "0000",
        "layout_uuid": layout_uuid,
        "receipt_printer_appliance_id": None,
        "cash_drawer_command": "none",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_drawer_command_requires_receipt_printer(db_session):
    db, event, layout = db_session
    with pytest.raises(HTTPException) as exc:
        assert_cash_registers_valid(
            db,
            event,
            [_register(layout.uuid, cash_drawer_command="escp_pin2")],
            [layout],
        )
    assert exc.value.detail["code"] == "cash_drawer_requires_receipt_printer"


def test_replace_configuration_persists_cash_drawer_command(db_session, monkeypatch):
    db, event, layout = db_session
    monkeypatch.setattr(
        "app.event_config_validation.event_printer_candidates",
        lambda _db, _event: [SimpleNamespace(id=99)],
    )
    replace_event_configuration(
        db,
        event,
        stations_in=[],
        event_waiters_in=[],
        app_layouts_in=[
            SimpleNamespace(
                uuid=layout.uuid,
                name=layout.name,
                is_default=True,
                grid_width=1,
                grid_height=1,
                cells=[],
            )
        ],
        cash_registers_in=[
            _register(
                layout.uuid,
                receipt_printer_appliance_id=99,
                cash_drawer_command="escp_pin5",
            )
        ],
    )
    db.commit()
    reg = db.query(EventCashRegister).filter(EventCashRegister.event_id == event.id).one()
    assert reg.cash_drawer_command == "escp_pin5"
