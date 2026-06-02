"""Sales report v3 resolves waiter and station UUIDs to display names."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.edge_reporting import build_sales_report_v3
from app.models import (
    Article,
    ArticleCategory,
    EdgeOrderItem,
    Event,
    EventStation,
    EventWaiter,
    HireCompany,
    Organisation,
)

WAITER_UUID = "11111111-1111-1111-1111-111111111111"
STATION_UUID = "22222222-2222-2222-2222-222222222222"
UNKNOWN_WAITER_UUID = "99999999-9999-9999-9999-999999999999"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    now = datetime.now(timezone.utc)
    db.add(HireCompany(id=1, name="HC"))
    db.add(Organisation(id=1, name="Org", country="CH", hire_company_id=1))
    db.add(ArticleCategory(id=1, name="Food", organisation_id=1))
    art = Article(id=10, name="Bratwurst", label="B", price=5.0, article_category_id=1)
    db.add(art)
    ev = Event(
        id=1,
        name="Fest",
        status="production",
        start=now,
        end=now,
        currency="EUR",
        organisation_id=1,
    )
    db.add(ev)
    st = EventStation(event_id=1, uuid=STATION_UUID, name="Grill", sort_order=0)
    db.add(st)
    db.add(EventWaiter(event_id=1, uuid=WAITER_UUID, name="Anna", pin="1234"))
    db.flush()
    st.articles = [art]
    db.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=100,
            submission_id=1,
            article_id=10,
            article_name="Bratwurst",
            station_uuid=STATION_UUID,
            waiter_uuid=WAITER_UUID,
            quantity=1,
            unit_price_cents=500,
            line_total_cents=500,
            payment_status="paid",
            method="cash",
            payload={},
        )
    )
    db.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=101,
            submission_id=2,
            article_id=10,
            article_name="Bratwurst",
            station_uuid=STATION_UUID,
            waiter_uuid=UNKNOWN_WAITER_UUID,
            quantity=1,
            unit_price_cents=500,
            line_total_cents=500,
            payment_status="paid",
            method="cash",
            payload={},
        )
    )
    db.commit()
    yield db
    db.close()


def test_sales_report_v3_resolves_waiter_and_station_names(db_session):
    report = build_sales_report_v3(db_session, organisation_id=1, event_id=1)
    assert report["currency"] == "EUR"
    by_waiter = {row["name"]: row for row in report["by_waiter"]}
    assert "Anna" in by_waiter
    assert by_waiter["Anna"]["order_count"] == 1
    assert by_waiter["Anna"]["line_cents"] == 500
    unknown = next(n for n in by_waiter if n.startswith("Kellner "))
    assert UNKNOWN_WAITER_UUID[:8] in unknown

    by_station = {row["name"]: row for row in report["by_station"]}
    assert "Grill" in by_station
    assert by_station["Grill"]["line_cents"] == 1000


def test_sales_report_v3_unknown_station_uuid_fallback(db_session):
    db_session.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=102,
            submission_id=3,
            article_id=10,
            article_name="Bratwurst",
            station_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            waiter_uuid=WAITER_UUID,
            quantity=1,
            unit_price_cents=300,
            line_total_cents=300,
            payment_status="open",
            method="cash",
            payload={},
        )
    )
    db_session.commit()
    report = build_sales_report_v3(db_session, organisation_id=1, event_id=1)
    station_names = [row["name"] for row in report["by_station"]]
    assert any(n.startswith("Station ") for n in station_names)
