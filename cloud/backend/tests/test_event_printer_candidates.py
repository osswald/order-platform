"""Event station printer options: overlap with open current and planned lendings."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, SessionLocal, engine
from app.event_config_validation import (
    assert_printer_eligible,
    event_printer_candidates,
)
from app.main import app
from app.models import (
    Appliance,
    ApplianceLending,
    Event,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_ORG_ADMIN
from app.security import get_password_hash

client = TestClient(app)


def _utc_dt(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def printer_scenario_db():
    """In-memory DB: event Jun 10–12, printer, multiple lendings."""
    engine_local = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_local)
    Session = sessionmaker(bind=engine_local)
    db = Session()
    hc = HireCompany(id=1, name="HC")
    org = Organisation(id=1, name="Org", country="CH", hire_company_id=1, currency="CHF")
    db.add_all([hc, org])
    printer = Appliance(
        id=10,
        hire_company_id=1,
        type="printer",
        name="Bar Printer",
        ip_address="192.168.1.50",
    )
    other_printer = Appliance(
        id=11,
        hire_company_id=1,
        type="printer",
        name="Other Printer",
        ip_address="192.168.1.51",
    )
    db.add_all([printer, other_printer])
    event = Event(
        id=1,
        name="Summer Fest",
        status="config",
        start=_utc_dt(2026, 6, 10),
        end=_utc_dt(2026, 6, 12, 23),
        organisation_id=1,
    )
    db.add(event)
    db.flush()
    yield db, event, printer, other_printer
    db.close()


def _add_lending(
    db,
    *,
    appliance_id: int,
    start: datetime,
    end: datetime,
    returned_at=None,
):
    start_d = start.date() if isinstance(start, datetime) else start
    end_d = end.date() if isinstance(end, datetime) else end
    row = ApplianceLending(
        appliance_id=appliance_id,
        organisation_id=1,
        start_date=start_d,
        end_date=end_d,
        returned_at=returned_at,
    )
    db.add(row)
    db.commit()
    return row


def _candidate_ids(db, event: Event) -> set[int]:
    return {a.id for a in event_printer_candidates(db, event)}


def test_planned_lending_overlapping_event_included(printer_scenario_db):
    db, event, printer, _other = printer_scenario_db
    _add_lending(
        db,
        appliance_id=printer.id,
        start=_utc_dt(2026, 6, 10),
        end=_utc_dt(2026, 6, 12),
    )
    assert printer.id in _candidate_ids(db, event)
    assert_printer_eligible(db, event, printer.id)


def test_current_lending_overlapping_event_included(printer_scenario_db):
    db, event, printer, _other = printer_scenario_db
    today = datetime.now(timezone.utc).date()
    _add_lending(
        db,
        appliance_id=printer.id,
        start=datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
        end=_utc_dt(2026, 6, 15),
    )
    assert printer.id in _candidate_ids(db, event)
    assert_printer_eligible(db, event, printer.id)


def test_planned_lending_outside_event_window_excluded(printer_scenario_db):
    db, event, printer, _other = printer_scenario_db
    _add_lending(
        db,
        appliance_id=printer.id,
        start=_utc_dt(2026, 8, 1),
        end=_utc_dt(2026, 8, 5),
    )
    assert printer.id not in _candidate_ids(db, event)
    with pytest.raises(HTTPException) as exc:
        assert_printer_eligible(db, event, printer.id)
    assert exc.value.status_code == 422


def test_ended_lending_before_event_excluded(printer_scenario_db):
    db, event, printer, _other = printer_scenario_db
    _add_lending(
        db,
        appliance_id=printer.id,
        start=_utc_dt(2026, 5, 1),
        end=_utc_dt(2026, 5, 5),
    )
    assert printer.id not in _candidate_ids(db, event)


def test_returned_lending_excluded(printer_scenario_db):
    db, event, printer, _other = printer_scenario_db
    _add_lending(
        db,
        appliance_id=printer.id,
        start=_utc_dt(2026, 6, 10),
        end=_utc_dt(2026, 6, 12),
        returned_at=datetime.now(timezone.utc),
    )
    assert printer.id not in _candidate_ids(db, event)


def _api_fixture(suffix: str) -> tuple[int, int, int, str, int]:
    suffix = f"{suffix}-{uuid4().hex}"
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Printer Event HC {suffix}")
        db.add(company)
        db.flush()
        org = Organisation(name=f"Printer Event Org {suffix}", country="CH", hire_company_id=company.id, currency="CHF")
        db.add(org)
        db.flush()
        user = User(
            email=f"printer-event-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORG_ADMIN,
            hire_company_id=company.id,
            is_superuser=False,
        )
        printer = Appliance(
            hire_company_id=company.id,
            type="printer",
            name=f"Event Printer {suffix}",
            ip_address="10.0.0.9",
        )
        db.add_all([user, printer])
        db.flush()
        event_start = datetime.now(timezone.utc) + timedelta(days=14)
        event_end = event_start + timedelta(days=2)
        event = Event(
            name=f"Future Fest {suffix}",
            status="config",
            start=event_start,
            end=event_end,
            organisation_id=org.id,
            payment_mode="pay_later",
        )
        db.add(event)
        db.commit()
        return event.id, printer.id, org.id, user.email, company.id
    finally:
        db.close()


def _token_for(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_configuration_api_lists_planned_printer():
    event_id, printer_id, org_id, email, _hc_id = _api_fixture("api")
    token = _token_for(email)
    lend_start = (datetime.now(timezone.utc) + timedelta(days=14)).date()
    lend_end = lend_start + timedelta(days=2)

    lend_resp = client.post(
        f"/appliances/{printer_id}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": org_id,
            "start_date": lend_start.isoformat(),
            "end_date": lend_end.isoformat(),
        },
    )
    assert lend_resp.status_code == 200, lend_resp.text

    cfg_resp = client.get(
        f"/events/{event_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cfg_resp.status_code == 200, cfg_resp.text
    printer_ids = {p["id"] for p in cfg_resp.json()["printer_options"]}
    assert printer_id in printer_ids

    summary_resp = client.get(
        f"/events/{event_id}/configuration?fields=summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()
    assert "printer_options" in summary
    for layout in summary.get("app_layouts", []):
        assert layout["cells"] == []
