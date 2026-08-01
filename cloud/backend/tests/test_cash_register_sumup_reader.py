"""Cash register default SumUp reader binding."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.database import Base, SessionLocal
from app.event_config_validation import replace_event_configuration
from app.main import app
from app.models import Event, EventAppLayout, EventCashRegister, HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.routers.events_helpers import serialize_event_configuration
from app.security import get_password_hash
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import country_id_by_code, ensure_country

client = TestClient(app)


def _register(layout_uuid: str, **kwargs):
    defaults = {
        "name": "Hauptkasse",
        "pickup_code_prefix": "A",
        "pin": "0000",
        "layout_uuid": layout_uuid,
        "receipt_printer_appliance_id": None,
        "cash_drawer_command": "none",
        "sumup_reader_id": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_replace_configuration_persists_sumup_reader_id():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ensure_country(db, "CH", country_id=1)
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, name="Org", country_id=1, hire_company_id=1, currency="CHF")
    db.add(org)
    now = datetime.now(UTC)
    event = Event(
        id=1,
        name="Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
        cash_registers_enabled=True,
    )
    db.add(event)
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
            _register(layout.uuid, sumup_reader_id="rdr_test1234567890123456789012"),
        ],
    )
    db.commit()
    reg = db.query(EventCashRegister).filter(EventCashRegister.event_id == event.id).one()
    assert reg.sumup_reader_id == "rdr_test1234567890123456789012"

    cfg = serialize_event_configuration(db, event)
    assert cfg.cash_registers[0].sumup_reader_id == "rdr_test1234567890123456789012"
    db.close()


def _api_seed() -> tuple[int, str, str, str]:
    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"CR SumUp HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"CR SumUp Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        event = Event(
            name="Fest",
            status="config",
            start=now,
            end=now,
            organisation_id=org.id,
            cash_registers_enabled=True,
        )
        db.add(event)
        db.flush()
        layout = EventAppLayout(
            event_id=event.id,
            uuid=f"layout-{suffix}",
            name="Kasse",
            is_default=True,
            grid_width=1,
            grid_height=1,
        )
        db.add(layout)
        db.flush()
        email = f"cr-sumup-{suffix}@test.local"
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return event.id, layout.uuid, email, suffix
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_configuration_api_round_trips_sumup_reader_id():
    event_id, layout_uuid, email, _suffix = _api_seed()
    headers = {
        "Authorization": f"Bearer {_token(email)}",
        "Content-Type": "application/json",
    }
    reader_id = "rdr_test1234567890123456789012"
    payload = {
        "stations": [],
        "event_waiters": [],
        "app_layouts": [
            {
                "uuid": layout_uuid,
                "name": "Kasse",
                "is_default": True,
                "grid_width": 1,
                "grid_height": 1,
                "cells": [],
            }
        ],
        "cash_registers": [
            {
                "name": "Hauptkasse",
                "pickup_code_prefix": "A",
                "pin": "0000",
                "layout_uuid": layout_uuid,
                "sumup_reader_id": reader_id,
            }
        ],
        "voucher_definitions": [],
        "kitchen_monitors": [],
    }
    resp = client.put(f"/events/{event_id}/configuration", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    reg = resp.json()["cash_registers"][0]
    assert reg["sumup_reader_id"] == reader_id

    get_resp = client.get(f"/events/{event_id}/configuration", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["cash_registers"][0]["sumup_reader_id"] == reader_id
