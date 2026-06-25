"""Dashboard summary helpers and organisation aggregation."""

from datetime import UTC, datetime, timedelta

import pytest
from app.dashboard_summary import (
    build_attention_items,
    build_organisation_dashboard_summary,
    events_by_status_counts,
    running_event_ids,
)
from app.database import Base
from app.models import Event, HireCompany, Organisation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _event(**kwargs):
    now = datetime.now(UTC)
    defaults = dict(
        name="Fest",
        status="config",
        start=now + timedelta(days=3),
        end=now + timedelta(days=4),
        organisation_id=1,
        payment_mode="pay_later",
        payment_types=["cash"],
    )
    defaults.update(kwargs)
    return Event(**defaults)


def test_events_by_status_counts():
    now = datetime.now(UTC)
    events = [
        _event(status="config"),
        _event(status="prod", start=now, end=now + timedelta(hours=2)),
        _event(status="archive", start=now - timedelta(days=10), end=now - timedelta(days=9)),
    ]
    counts = events_by_status_counts(events)
    assert counts["config"] == 1
    assert counts["prod"] == 1
    assert counts["archive"] == 1
    assert counts["test"] == 0


def test_running_event_ids():
    now = datetime.now(UTC)
    running = _event(
        id=10,
        status="prod",
        start=now - timedelta(hours=1),
        end=now + timedelta(hours=1),
    )
    future = _event(
        id=11,
        status="prod",
        start=now + timedelta(days=1),
        end=now + timedelta(days=2),
    )
    assert running_event_ids([running, future], now) == [10]


def test_attention_config_starting_soon():
    now = datetime.now(UTC)
    events = [_event(status="config", start=now + timedelta(days=2))]
    items = build_attention_items(events, now)
    assert len(items) == 1
    assert items[0]["type"] == "config_starting_soon"
    assert "message" not in items[0]
    assert items[0]["event_name"] == "Fest"


def test_attention_missing_twint_qr():
    now = datetime.now(UTC)
    events = [
        _event(
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
            payment_types=["cash", "twint"],
        )
    ]
    items = build_attention_items(events, now)
    assert any(i["type"] == "missing_twint_qr" for i in items)


def test_build_organisation_dashboard_summary(db):
    ch_country_id = ensure_country(db, "CH", country_id=1)
    now = datetime.now(UTC)
    db.add(HireCompany(id=1, name="HC"))
    org = Organisation(id=1, hire_company_id=1, name="Test Org", country_id=ch_country_id, currency="CHF")
    db.add(org)
    db.add(
        _event(
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
    )
    db.commit()
    events = db.query(Event).filter(Event.organisation_id == 1).all()
    summary = build_organisation_dashboard_summary(db, org, events)
    assert summary["organisation_name"] == "Test Org"
    assert "status_labels" not in summary
    assert summary["events_total"] == 1
    assert summary["catalog"]["waiters"] == 0
    assert "sales" in summary
    assert "onboarding" in summary
    assert summary["onboarding"]["dismissed"] is False
    assert summary["sales"]["totals"]["distinct_orders_count"] == 0
