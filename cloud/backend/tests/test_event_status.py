"""Event status lifecycle: transitions, purge on test→prod, edge bundle filter."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.event_status import (
    assert_create_status,
    purge_event_operational_data,
    validate_status_transition,
)
from app.models import (
    EdgeSubmittedOrder,
    Event,
    EventArticleStock,
    EventCollectiveBill,
    Organisation,
)
from app.routers.edge import _active_events_for_org
from app.stock import reset_event_stock_to_baseline


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    org = Organisation(id=1, name="Org", country="CH")
    event = Event(
        id=1,
        name="Fest",
        status="test",
        start=now - timedelta(hours=1),
        end=now + timedelta(hours=1),
        currency="CHF",
        organisation_id=1,
        payment_mode="pay_later",
        payment_types=["cash"],
    )
    session.add_all([org, event])
    session.add(
        EventArticleStock(
            event_id=1,
            article_id=10,
            monitor_stock=True,
            in_stock=5,
            baseline_in_stock=20,
        )
    )
    session.add(
        EdgeSubmittedOrder(
            client_order_id="o1",
            appliance_id=1,
            organisation_id=1,
            event_id=1,
            payload={"lines": []},
        )
    )
    session.add(EventCollectiveBill(uuid="cb1", event_id=1, name="Team", appliance_id=1))
    session.commit()
    yield session
    session.close()


def test_validate_status_transition_allows_forward_only():
    validate_status_transition("config", "test")
    validate_status_transition("test", "prod")
    validate_status_transition("prod", "archive")
    validate_status_transition("test", "test")

    with pytest.raises(HTTPException) as exc:
        validate_status_transition("test", "config")
    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        validate_status_transition("config", "prod")
    assert exc.value.status_code == 422


def test_assert_create_status_config_only():
    assert assert_create_status("config") == "config"
    with pytest.raises(HTTPException):
        assert_create_status("test")


def test_purge_event_operational_data(db):
    event = db.query(Event).filter(Event.id == 1).first()
    purge_event_operational_data(db, event)
    db.commit()

    assert db.query(EdgeSubmittedOrder).count() == 0
    assert db.query(EventCollectiveBill).count() == 0
    stock = db.query(EventArticleStock).filter(EventArticleStock.event_id == 1).first()
    assert stock.in_stock == 20


def test_reset_event_stock_to_baseline(db):
    event = db.query(Event).filter(Event.id == 1).first()
    reset_event_stock_to_baseline(db, event)
    db.commit()
    stock = db.query(EventArticleStock).filter(EventArticleStock.event_id == 1).first()
    assert stock.in_stock == 20


def test_reset_event_stock_to_baseline_skips_without_baseline(db):
    stock = db.query(EventArticleStock).filter(EventArticleStock.event_id == 1).first()
    stock.baseline_in_stock = None
    stock.in_stock = 3
    db.commit()
    event = db.query(Event).filter(Event.id == 1).first()
    reset_event_stock_to_baseline(db, event)
    assert stock.in_stock == 3


def test_active_events_for_org_excludes_config_and_archive(db):
    now = datetime.now(timezone.utc)
    db.add(
        Event(
            id=2,
            name="Config",
            status="config",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
            currency="CHF",
            organisation_id=1,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
    )
    db.add(
        Event(
            id=3,
            name="Archive",
            status="archive",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
            currency="CHF",
            organisation_id=1,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
    )
    db.add(
        Event(
            id=4,
            name="Prod",
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
            currency="CHF",
            organisation_id=1,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
    )
    db.commit()

    active = _active_events_for_org(db, 1)
    ids = {e.id for e in active}
    assert ids == {1, 4}
