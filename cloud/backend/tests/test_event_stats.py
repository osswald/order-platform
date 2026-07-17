"""Event stats reporting with timeframe and article timeline buckets."""

from datetime import UTC, datetime, timedelta

import pytest
from app.database import Base
from app.event_stats import (
    build_event_stats,
    event_article_ids,
    event_category_ids,
    parse_ordered_at,
)
from app.models import (
    Article,
    ArticleCategory,
    EdgeOrderItem,
    Event,
    EventCashRegister,
    EventStation,
    EventWaiter,
    HireCompany,
    Organisation,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country

WAITER_UUID = "11111111-1111-1111-1111-111111111111"
CASH_REGISTER_UUID = "33333333-3333-3333-3333-333333333333"
STATION_UUID = "22222222-2222-2222-2222-222222222222"
ARTICLE_A = 10
ARTICLE_B = 11

RANGE_START = datetime(2026, 6, 25, 10, 0, tzinfo=UTC)
RANGE_END = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch_country_id = ensure_country(db, "CH", country_id=1)
    db.add(HireCompany(id=1, name="HC"))
    db.add(Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF"))
    db.add(ArticleCategory(id=1, name="Food", organisation_id=1))
    db.add(ArticleCategory(id=2, name="Drinks", organisation_id=1))
    art_a = Article(id=ARTICLE_A, name="Bratwurst", label="B", price=5.0, article_category_id=1)
    art_b = Article(id=ARTICLE_B, name="Bier", label="Bi", price=4.0, article_category_id=2)
    db.add(art_a)
    db.add(art_b)
    ev = Event(
        id=1,
        name="Fest",
        status="prod",
        start=RANGE_START - timedelta(hours=1),
        end=RANGE_END + timedelta(hours=1),
        organisation_id=1,
    )
    db.add(ev)
    st = EventStation(event_id=1, uuid=STATION_UUID, name="Grill", sort_order=0)
    db.add(st)
    db.add(EventWaiter(event_id=1, uuid=WAITER_UUID, name="Anna", pin="1234"))
    db.flush()
    st.articles = [art_a, art_b]
    db.commit()
    yield db
    db.close()


def _add_item(
    db,
    *,
    article_id: int,
    article_name: str,
    ordered_at: datetime,
    qty: int = 1,
    line_cents: int = 500,
    payment_status: str = "paid",
    method: str = "cash",
    submission_id: int,
    session_id: int = 100,
    waiter_uuid: str | None = WAITER_UUID,
    order_source: str = "waiter",
    cash_register_uuid: str | None = None,
):
    db.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=session_id,
            submission_id=submission_id,
            article_id=article_id,
            article_name=article_name,
            station_uuid=STATION_UUID,
            waiter_uuid=waiter_uuid,
            cash_register_uuid=cash_register_uuid,
            order_source=order_source,
            quantity=qty,
            unit_price_cents=line_cents,
            line_total_cents=line_cents * qty,
            payment_status=payment_status,
            method=method,
            ordered_at=ordered_at,
            payload={},
        )
    )


def test_parse_ordered_at_from_iso_string():
    dt = parse_ordered_at("2026-06-25T10:30:00+00:00")
    assert dt == datetime(2026, 6, 25, 10, 30, tzinfo=UTC)


def test_parse_ordered_at_from_iso_string_with_z_suffix():
    dt = parse_ordered_at("2026-06-25T10:30:00Z")
    assert dt == datetime(2026, 6, 25, 10, 30, tzinfo=UTC)


def test_parse_ordered_at_from_offsetless_iso_string_assumes_utc():
    dt = parse_ordered_at("2026-06-25T10:30:00")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt == datetime(2026, 6, 25, 10, 30, tzinfo=UTC)


def test_parse_ordered_at_from_naive_datetime_assumes_utc():
    dt = parse_ordered_at(datetime(2026, 6, 25, 10, 30))
    assert dt == datetime(2026, 6, 25, 10, 30, tzinfo=UTC)


def test_parse_ordered_at_invalid_inputs_return_none():
    assert parse_ordered_at(None) is None
    assert parse_ordered_at("") is None
    assert parse_ordered_at("   ") is None
    assert parse_ordered_at("not-a-date") is None


def test_event_article_ids_from_stations(db_session):
    ids = event_article_ids(db_session, event_id=1, organisation_id=1)
    assert ids == {ARTICLE_A, ARTICLE_B}


def test_build_event_stats_filters_by_timeframe(db_session):
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + timedelta(minutes=30),
        submission_id=1,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_END + timedelta(hours=1),
        submission_id=2,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        article_ids=[ARTICLE_A],
    )
    assert report["totals"]["distinct_orders_count"] == 1
    assert report["totals"]["line_cents"] == 500


def test_build_event_stats_article_timeline_24_buckets(db_session):
    bucket_width = (RANGE_END - RANGE_START) / 24
    t0 = RANGE_START + bucket_width * 2
    t1 = RANGE_START + bucket_width * 2 + timedelta(seconds=1)
    t2 = RANGE_START + bucket_width * 5
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=t0,
        qty=2,
        line_cents=500,
        submission_id=1,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=t1,
        qty=1,
        line_cents=500,
        submission_id=2,
        session_id=101,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_B,
        article_name="Bier",
        ordered_at=t2,
        qty=4,
        line_cents=400,
        submission_id=3,
        session_id=102,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        article_ids=[ARTICLE_A, ARTICLE_B],
    )
    timeline = report["article_timeline"]
    assert timeline["bucket_count"] == 24
    assert len(timeline["buckets"]) == 24
    assert len(timeline["series"]) == 2

    bratwurst = next(s for s in timeline["series"] if s["article_id"] == ARTICLE_A)
    bier = next(s for s in timeline["series"] if s["article_id"] == ARTICLE_B)
    assert sum(bratwurst["qty"]) == 3
    assert bratwurst["qty"][2] == 3
    assert sum(bier["qty"]) == 4
    assert bier["qty"][5] == 4

    totals = {t["article_id"]: t["qty"] for t in timeline["totals"]}
    assert totals[ARTICLE_A] == 3
    assert totals[ARTICLE_B] == 4


def test_build_event_stats_empty_article_ids_timeline(db_session):
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + timedelta(minutes=10),
        submission_id=1,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        article_ids=[],
    )
    assert report["article_timeline"]["series"] == []
    assert report["totals"]["distinct_orders_count"] == 1


def test_build_event_stats_article_filter_narrows_breakdowns(db_session):
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + timedelta(minutes=10),
        line_cents=500,
        submission_id=1,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_B,
        article_name="Bier",
        ordered_at=RANGE_START + timedelta(minutes=20),
        line_cents=400,
        method="twint",
        submission_id=2,
        session_id=101,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        article_ids=[ARTICLE_A],
    )
    assert report["totals"]["line_cents"] == 500
    assert len(report["by_payment_type"]) == 1
    assert report["by_payment_type"][0]["type"] == "cash"


def test_event_category_ids_from_event_articles(db_session):
    ids = event_category_ids(db_session, event_id=1, organisation_id=1)
    assert ids == {1, 2}


def test_build_event_stats_category_timeline_24_buckets(db_session):
    bucket_width = (RANGE_END - RANGE_START) / 24
    t0 = RANGE_START + bucket_width * 2
    t1 = RANGE_START + bucket_width * 5
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=t0,
        qty=2,
        submission_id=1,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_B,
        article_name="Bier",
        ordered_at=t1,
        qty=4,
        submission_id=2,
        session_id=101,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        category_ids=[1, 2],
    )
    timeline = report["category_timeline"]
    assert timeline["bucket_count"] == 24
    assert len(timeline["series"]) == 2

    food = next(s for s in timeline["series"] if s["category_id"] == 1)
    drinks = next(s for s in timeline["series"] if s["category_id"] == 2)
    assert sum(food["qty"]) == 2
    assert sum(drinks["qty"]) == 4


def test_build_event_stats_by_waiter_uses_cash_register_name(db_session):
    db_session.add(
        EventCashRegister(
            event_id=1,
            uuid=CASH_REGISTER_UUID,
            name="Hauptkasse",
            sort_order=0,
            pickup_code_prefix="HK",
            pin="1234",
            layout_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        )
    )
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + timedelta(minutes=10),
        qty=2,
        submission_id=1,
        waiter_uuid=None,
        order_source="cash_register",
        cash_register_uuid=CASH_REGISTER_UUID,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
    )
    assert report["by_waiter"][0]["name"] == "Hauptkasse"
    assert report["by_waiter"][0]["qty"] == 2


def test_build_event_stats_by_waiter_includes_qty(db_session):
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + timedelta(minutes=10),
        qty=3,
        submission_id=1,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
    )
    assert report["by_waiter"][0]["qty"] == 3


def test_build_event_stats_rejects_unknown_category_ids(db_session):
    with pytest.raises(ValueError, match="invalid_category_ids"):
        build_event_stats(
            db_session,
            organisation_id=1,
            event_id=1,
            from_dt=RANGE_START,
            to_dt=RANGE_END,
            category_ids=[999],
        )


def test_build_event_stats_rejects_unknown_article_ids(db_session):
    with pytest.raises(ValueError, match="invalid_article_ids"):
        build_event_stats(
            db_session,
            organisation_id=1,
            event_id=1,
            from_dt=RANGE_START,
            to_dt=RANGE_END,
            article_ids=[999],
        )


def test_build_event_stats_revenue_timeline_and_aov(db_session):
    bucket_width = (RANGE_END - RANGE_START) / 24
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + bucket_width * 2,
        qty=2,
        line_cents=500,
        submission_id=1,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_B,
        article_name="Bier",
        ordered_at=RANGE_START + bucket_width * 2 + timedelta(seconds=1),
        qty=1,
        line_cents=400,
        submission_id=2,
        session_id=101,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
    )
    assert report["totals"]["line_cents"] == 1400
    assert report["totals"]["distinct_orders_count"] == 2
    assert report["totals"]["average_order_value_cents"] == 700

    revenue = report["revenue_timeline"]
    assert revenue["bucket_count"] == 24
    assert len(revenue["line_cents"]) == 24
    assert sum(revenue["line_cents"]) == 1400
    assert revenue["line_cents"][2] == 1400


def test_build_event_stats_top_articles_and_order_source(db_session):
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + timedelta(minutes=10),
        qty=5,
        line_cents=500,
        submission_id=1,
    )
    _add_item(
        db_session,
        article_id=ARTICLE_B,
        article_name="Bier",
        ordered_at=RANGE_START + timedelta(minutes=20),
        qty=1,
        line_cents=400,
        submission_id=2,
        session_id=101,
        waiter_uuid=None,
        order_source="cash_register",
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        article_ids=[ARTICLE_A],
    )
    assert report["totals"]["line_cents"] == 2500
    assert len(report["top_articles"]) == 2
    top_by_qty = sorted(report["top_articles"], key=lambda row: row["qty"], reverse=True)
    assert top_by_qty[0]["article_id"] == ARTICLE_A
    assert top_by_qty[0]["qty"] == 5
    assert top_by_qty[1]["line_cents"] == 400

    sources = {row["source"]: row for row in report["by_order_source"]}
    assert sources["waiter"]["qty"] == 5
    assert sources["cash_register"]["qty"] == 1


def test_build_event_stats_bucket_count_48(db_session):
    bucket_width = (RANGE_END - RANGE_START) / 48
    _add_item(
        db_session,
        article_id=ARTICLE_A,
        article_name="Bratwurst",
        ordered_at=RANGE_START + bucket_width * 10,
        qty=1,
        submission_id=1,
    )
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
        article_ids=[ARTICLE_A],
        bucket_count=48,
    )
    assert report["article_timeline"]["bucket_count"] == 48
    assert report["revenue_timeline"]["bucket_count"] == 48
    bratwurst = report["article_timeline"]["series"][0]
    assert bratwurst["qty"][10] == 1


def test_build_event_stats_rejects_invalid_bucket_count(db_session):
    with pytest.raises(ValueError, match="invalid_bucket_count"):
        build_event_stats(
            db_session,
            organisation_id=1,
            event_id=1,
            from_dt=RANGE_START,
            to_dt=RANGE_END,
            bucket_count=36,
        )
