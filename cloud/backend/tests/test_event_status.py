"""Event status lifecycle: transitions, purge on test→prod, edge bundle filter."""

from datetime import UTC, datetime, timedelta

import pytest
from app.database import Base
from app.event_status import (
    assert_create_status,
    purge_event_operational_data,
    validate_status_transition,
)
from app.models import (
    Appliance,
    EdgeCashSession,
    EdgeKitchenTicketSnapshot,
    EdgeOrderItem,
    EdgeOrderSession,
    EdgeOrderSnapshot,
    EdgePayment,
    EdgePaymentBatch,
    EdgeSubmittedOrder,
    Event,
    EventArticleStock,
    EventCollectiveBill,
    EventVoucherRedemption,
    HireCompany,
    Organisation,
)
from app.routers.edge import _active_events_for_org
from app.stock import reset_event_stock_to_baseline
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    ch_country_id = ensure_country(session, "CH", country_id=1)
    now = datetime.now(UTC)
    hc = HireCompany(id=1, name="HC")
    org = Organisation(id=1, hire_company_id=1, name="Org", country_id=ch_country_id, currency="CHF")
    appliance = Appliance(id=1, hire_company_id=1, type="pi", name="Pi")
    event = Event(
        id=1,
        name="Fest",
        status="test",
        start=now - timedelta(hours=1),
        end=now + timedelta(hours=1),
        organisation_id=1,
        payment_mode="pay_later",
        payment_types=["cash"],
    )
    session.add_all([hc, org, appliance, event])
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
    session.add(
        EdgeOrderSession(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=100,
            table_number=1,
            order_source="waiter",
        )
    )
    session.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=100,
            submission_id=1,
            article_id=10,
            article_name="Bier",
            quantity=1,
            unit_price_cents=500,
            line_total_cents=500,
            payment_status="paid",
            method="cash",
            payload={},
        )
    )
    session.add(
        EdgePaymentBatch(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            batch_uuid="batch-1",
            name="Team",
            status="open",
            total_cents=500,
        )
    )
    session.add(
        EdgePayment(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            submission_id=1,
            payment_batch_uuid="batch-1",
            method="cash",
            amount_cents=500,
            payload={"type": "cash", "amount_cents": 500},
        )
    )
    session.add(
        EdgeOrderSnapshot(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            logical_client_order_id="o1",
            payload={"lines": []},
        )
    )
    session.add(
        EdgeKitchenTicketSnapshot(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            logical_client_order_id="o1",
            payload={"tickets": []},
        )
    )
    session.add(
        EdgeCashSession(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            cash_session_id=1,
            subject_name="Anna",
            status="OPEN",
            payload={},
        )
    )
    session.add(
        EventVoucherRedemption(
            event_id=1,
            voucher_definition_uuid="voucher-uuid-1",
            payment_client_order_id="o1",
            kind="fixed_amount",
            applied_cents=100,
        )
    )
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

    assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == 1).count() == 0
    assert db.query(EdgeOrderSnapshot).filter(EdgeOrderSnapshot.event_id == 1).count() == 0
    assert db.query(EdgeKitchenTicketSnapshot).filter(EdgeKitchenTicketSnapshot.event_id == 1).count() == 0
    assert db.query(EdgeCashSession).filter(EdgeCashSession.event_id == 1).count() == 0
    assert db.query(EventCollectiveBill).filter(EventCollectiveBill.event_id == 1).count() == 0
    assert db.query(EdgeOrderSession).filter(EdgeOrderSession.event_id == 1).count() == 0
    assert db.query(EdgeOrderItem).filter(EdgeOrderItem.event_id == 1).count() == 0
    assert db.query(EdgePaymentBatch).filter(EdgePaymentBatch.event_id == 1).count() == 0
    assert db.query(EdgePayment).filter(EdgePayment.event_id == 1).count() == 0
    assert db.query(EventVoucherRedemption).filter(EventVoucherRedemption.event_id == 1).count() == 0
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
    now = datetime.now(UTC)
    db.add(
        Event(
            id=2,
            name="Config",
            status="config",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
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
            organisation_id=1,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
    )
    db.commit()

    active = _active_events_for_org(db, 1)
    ids = {e.id for e in active}
    assert ids == {1, 4}
