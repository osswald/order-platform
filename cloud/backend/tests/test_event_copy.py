"""Event copy duplicates configuration but not sales data."""

from datetime import UTC, datetime

import pytest
from app.database import Base
from app.event_copy import copy_event, default_copy_name
from app.models import (
    Article,
    ArticleCategory,
    EdgeSubmittedOrder,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventArticleStock,
    EventCollectiveBill,
    EventStation,
    EventWaiter,
    HireCompany,
    Organisation,
)
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

    hire = HireCompany(id=1, name="Vendor")
    org = Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF")
    session.add(hire)
    cat = ArticleCategory(id=1, name="Drinks", organisation_id=1)
    art = Article(
        id=10,
        name="Beer",
        label="B",
        price=5.0,
        article_category_id=1,
    )
    event = Event(
        id=1,
        name="Source Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
        payment_types=["cash", "twint"],
        twint_qr_mime="image/png",
        twint_qr_data="abc123",
        receipt_printing_config={
            "label_event_title": "Copied Fest",
            "station_receipt": {"bottom_line": "Kitchen"},
        },
        receipt_logo_mime="image/png",
        receipt_logo_data="logo123",
    )
    session.add_all([org, cat, art, event])
    session.flush()

    st = EventStation(
        event_id=1,
        uuid="st-uuid-src",
        name="Bar",
        sort_order=0,
        kitchen_monitor_enabled=True,
    )
    st.articles = [art]
    session.add(st)
    session.add(EventWaiter(event_id=1, uuid="ew-uuid-src", name="Anna", pin="1234"))
    session.flush()

    lo = EventAppLayout(event_id=1, name="Main", is_default=True, grid_width=2, grid_height=2)
    session.add(lo)
    session.flush()
    cell = EventAppLayoutCell(layout_id=lo.id, row=0, col=0, label="Beer", color="#fff")
    cell.articles = [art]
    session.add(cell)

    session.add(
        EventArticleStock(event_id=1, article_id=10, monitor_stock=True, in_stock=15)
    )
    session.add(
        EdgeSubmittedOrder(
            client_order_id="order-src-1",
            appliance_id=1,
            organisation_id=1,
            event_id=1,
            payload={"payment_status": "paid", "lines": []},
        )
    )
    session.add(
        EventCollectiveBill(
            uuid="cb-src",
            event_id=1,
            name="Personal",
            appliance_id=1,
        )
    )
    session.commit()
    yield session
    session.close()


def test_default_copy_name():
    assert default_copy_name("Fest") == "Fest (Kopie)"
    assert default_copy_name("Fest (Kopie)") == "Fest (Kopie)"


def test_copy_event_clones_config_not_sales(db):
    source = (
        db.query(Event)
        .filter(Event.id == 1)
        .first()
    )
    source_stations = db.query(EventStation).filter(EventStation.event_id == 1).all()
    source_waiters = db.query(EventWaiter).filter(EventWaiter.event_id == 1).all()

    new_event = copy_event(db, source, name="Source Fest (Kopie)")
    db.commit()

    assert new_event.id != source.id
    assert new_event.name == "Source Fest (Kopie)"
    assert new_event.status == "config"
    assert new_event.twint_qr_mime == "image/png"
    assert new_event.twint_qr_data == "abc123"
    assert new_event.receipt_logo_mime == "image/png"
    assert new_event.receipt_logo_data == "logo123"
    assert new_event.receipt_printing_config["label_event_title"] == "Copied Fest"
    assert new_event.receipt_printing_config["station_receipt"]["bottom_line"] == "Kitchen"

    new_stations = db.query(EventStation).filter(EventStation.event_id == new_event.id).all()
    new_waiters = db.query(EventWaiter).filter(EventWaiter.event_id == new_event.id).all()
    assert len(new_stations) == 1
    assert len(new_waiters) == 1
    assert new_stations[0].uuid != source_stations[0].uuid
    assert new_waiters[0].uuid != source_waiters[0].uuid
    assert new_stations[0].name == "Bar"
    assert new_stations[0].kitchen_monitor_enabled is False
    assert [a.id for a in new_stations[0].articles] == [10]

    layouts = db.query(EventAppLayout).filter(EventAppLayout.event_id == new_event.id).all()
    assert len(layouts) == 1
    cells = db.query(EventAppLayoutCell).filter(EventAppLayoutCell.layout_id == layouts[0].id).all()
    assert len(cells) == 1

    stock = (
        db.query(EventArticleStock)
        .filter(EventArticleStock.event_id == new_event.id, EventArticleStock.article_id == 10)
        .first()
    )
    assert stock is not None
    assert stock.monitor_stock is True
    assert stock.in_stock == 15

    assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == new_event.id).count() == 0
    assert db.query(EventCollectiveBill).filter(EventCollectiveBill.event_id == new_event.id).count() == 0

    assert db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.event_id == 1).count() == 1
