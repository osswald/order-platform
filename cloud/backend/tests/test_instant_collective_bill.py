"""Instant collective bill settings and validation."""

from datetime import UTC, datetime

import pytest
from app.instant_collective_bill import apply_instant_collective_bill_settings
from app.models import Event, HireCompany, Organisation

from tests.helpers import ensure_country


@pytest.fixture
def event_row(memory_db_session):
    ch = ensure_country(memory_db_session, "CH", country_id=1)
    hc = HireCompany(id=1, name="HC")
    memory_db_session.add(hc)
    org = Organisation(id=1, hire_company_id=1, name="Org", country_id=ch, currency="CHF")
    memory_db_session.add(org)
    now = datetime.now(UTC)
    ev = Event(
        id=1,
        name="Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
    )
    memory_db_session.add(ev)
    memory_db_session.commit()
    return ev


def test_instant_mode_requires_collective_bill_name(event_row, memory_db_session):
    with pytest.raises(Exception):
        apply_instant_collective_bill_settings(
            event_row,
            payment_mode="instant",
            instant_collective_bill_name="",
            payment_mode_set=True,
            instant_collective_bill_name_set=True,
        )


def test_instant_mode_sets_uuid(event_row, memory_db_session):
    apply_instant_collective_bill_settings(
        event_row,
        payment_mode="instant",
        instant_collective_bill_name="Veranstalter",
        payment_mode_set=True,
        instant_collective_bill_name_set=True,
    )
    assert event_row.instant_collective_bill_name == "Veranstalter"
    assert event_row.instant_collective_bill_uuid


def test_switching_away_from_instant_clears_fields(event_row, memory_db_session):
    apply_instant_collective_bill_settings(
        event_row,
        payment_mode="instant",
        instant_collective_bill_name="Veranstalter",
        payment_mode_set=True,
        instant_collective_bill_name_set=True,
    )
    apply_instant_collective_bill_settings(
        event_row,
        payment_mode="pay_later",
        payment_mode_set=True,
    )
    assert event_row.instant_collective_bill_name is None
    assert event_row.instant_collective_bill_uuid is None
