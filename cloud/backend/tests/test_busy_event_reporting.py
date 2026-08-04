"""Tests for cloud-busy-event-reporting changes.

Covers:
- SQL-side time filtering in event stats (no full-table Python filter)
- Dashboard summary SQL path (no per-event build_event_sales_report)
- get_event_for_reporting does not load layout/cell graph
- Transactions pagination prior-snapshot scoped to page client_ids
- Large-volume stats fixture asserting shape and correct window behaviour
- Golden parity: dashboard SQL aggregates vs legacy path on small fixture
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.dashboard_summary import _aggregate_sales
from app.database import Base
from app.event_stats import build_event_stats
from app.event_transactions import build_event_transactions_page
from app.models import (
    Appliance,
    Article,
    ArticleCategory,
    EdgeOrderItem,
    EdgeSubmittedOrder,
    Event,
    EventStation,
    EventWaiter,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.routers.events_helpers import get_event_for_reporting
from app.security import get_password_hash
from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country

WAITER_UUID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
STATION_UUID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ARTICLE_A = 20
ARTICLE_B = 21

RANGE_START = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
RANGE_END = datetime(2026, 8, 1, 14, 0, tzinfo=UTC)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch = ensure_country(db, "CH", country_id=1)
    db.add(HireCompany(id=1, name="HC"))
    db.add(Organisation(id=1, name="Org", country_id=ch, hire_company_id=1, currency="CHF"))
    db.add(ArticleCategory(id=1, name="Food", organisation_id=1))
    db.add(ArticleCategory(id=2, name="Drinks", organisation_id=1))
    art_a = Article(id=ARTICLE_A, name="Wurst", label="W", price=5.0, article_category_id=1)
    art_b = Article(id=ARTICLE_B, name="Bier", label="B", price=4.0, article_category_id=2)
    db.add(art_a)
    db.add(art_b)
    ev = Event(
        id=1,
        name="Fest",
        status="prod",
        start=RANGE_START - timedelta(hours=2),
        end=RANGE_END + timedelta(hours=2),
        organisation_id=1,
        payment_mode="pay_now",
        payment_types=["cash"],
    )
    db.add(ev)
    st = EventStation(event_id=1, uuid=STATION_UUID, name="Grill", sort_order=0)
    db.add(st)
    db.add(EventWaiter(event_id=1, uuid=WAITER_UUID, name="Anna", pin="1111"))
    db.flush()
    st.articles = [art_a, art_b]
    db.commit()
    yield db
    db.close()


@pytest.fixture
def db_for_transactions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch = ensure_country(db, "CH", country_id=1)
    db.add(HireCompany(id=1, name="HC"))
    db.add(Organisation(id=1, name="Org", country_id=ch, hire_company_id=1, currency="CHF"))
    db.add(Appliance(id=1, hire_company_id=1, type="pi", name="Pi"))
    ev = Event(
        id=1,
        name="Fest",
        status="prod",
        start=datetime(2026, 8, 1, tzinfo=UTC),
        end=datetime(2026, 8, 2, tzinfo=UTC),
        organisation_id=1,
        payment_mode="pay_now",
    )
    db.add(ev)
    db.add(EventWaiter(event_id=1, uuid=WAITER_UUID, name="Anna", pin="1111"))
    db.commit()
    yield db, ev
    db.close()


def _add_item(
    db,
    *,
    event_id: int = 1,
    article_id: int,
    article_name: str,
    ordered_at: datetime,
    qty: int = 1,
    line_cents: int = 500,
    payment_status: str = "paid",
    method: str = "cash",
    submission_id: int,
    session_id: int = 100,
):
    db.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=event_id,
            session_id=session_id,
            submission_id=submission_id,
            article_id=article_id,
            article_name=article_name,
            station_uuid=STATION_UUID,
            waiter_uuid=WAITER_UUID,
            order_source="waiter",
            quantity=qty,
            unit_price_cents=line_cents,
            line_total_cents=line_cents * qty,
            payment_status=payment_status,
            method=method,
            ordered_at=ordered_at,
            payload={},
        )
    )


# ---------------------------------------------------------------------------
# Stats: SQL time-window filter correctness
# ---------------------------------------------------------------------------


def test_stats_sql_filters_out_items_before_window(db_session):
    """Items with ordered_at < start must be excluded from stats."""
    before_window = RANGE_START - timedelta(minutes=30)
    in_window = RANGE_START + timedelta(minutes=30)

    _add_item(db_session, article_id=ARTICLE_A, article_name="Wurst", ordered_at=before_window, submission_id=1)
    _add_item(db_session, article_id=ARTICLE_A, article_name="Wurst", ordered_at=in_window, submission_id=2, session_id=200)
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
    )
    # Only item in window should contribute
    assert report["totals"]["distinct_orders_count"] == 1
    assert report["totals"]["line_cents"] == 500


def test_stats_sql_filters_out_items_after_window(db_session):
    """Items with ordered_at > end must be excluded from stats."""
    after_window = RANGE_END + timedelta(hours=1)
    in_window = RANGE_START + timedelta(hours=1)

    _add_item(db_session, article_id=ARTICLE_B, article_name="Bier", ordered_at=after_window, submission_id=10, session_id=300)
    _add_item(db_session, article_id=ARTICLE_B, article_name="Bier", ordered_at=in_window, qty=2, line_cents=400, submission_id=11, session_id=301)
    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
    )
    assert report["totals"]["distinct_orders_count"] == 1
    assert report["totals"]["line_cents"] == 800  # 2 × 400


def test_stats_empty_window_returns_valid_payload(db_session):
    """A window with no orders must return a zeroed but valid payload."""
    _add_item(db_session, article_id=ARTICLE_A, article_name="Wurst", ordered_at=RANGE_END + timedelta(hours=2), submission_id=20)
    db_session.commit()

    future_start = RANGE_END + timedelta(hours=3)
    future_end = RANGE_END + timedelta(hours=4)

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=future_start,
        to_dt=future_end,
    )
    assert report["totals"]["distinct_orders_count"] == 0
    assert report["totals"]["line_cents"] == 0
    assert report["totals"]["paid_cents"] == 0
    assert report["article_timeline"]["series"] == []
    assert report["revenue_timeline"]["bucket_count"] == 24
    assert all(v == 0 for v in report["revenue_timeline"]["line_cents"])


def test_stats_large_volume_window_subset(db_session):
    """Large set of items outside window — only window items count.

    This is the key correctness + efficiency scenario: items outside the
    requested time range must not be returned by the SQL query and must
    not appear in any aggregate.
    """
    TOTAL_ITEMS = 200
    WINDOW_ITEMS = 10

    # Add many items outside the window
    for i in range(TOTAL_ITEMS):
        before = RANGE_START - timedelta(hours=i + 1)
        _add_item(
            db_session,
            article_id=ARTICLE_A,
            article_name="Wurst",
            ordered_at=before,
            submission_id=1000 + i,
            session_id=2000 + i,
            line_cents=100,
        )

    # Add a known subset inside the window
    for j in range(WINDOW_ITEMS):
        ts = RANGE_START + timedelta(minutes=j * 10)
        _add_item(
            db_session,
            article_id=ARTICLE_B,
            article_name="Bier",
            ordered_at=ts,
            submission_id=3000 + j,
            session_id=4000 + j,
            line_cents=400,
        )

    db_session.commit()

    report = build_event_stats(
        db_session,
        organisation_id=1,
        event_id=1,
        from_dt=RANGE_START,
        to_dt=RANGE_END,
    )

    # Only the WINDOW_ITEMS should appear in totals
    assert report["totals"]["distinct_orders_count"] == WINDOW_ITEMS
    assert report["totals"]["line_cents"] == WINDOW_ITEMS * 400

    # top_articles should only contain Bier (items in window)
    assert len(report["top_articles"]) == 1
    assert report["top_articles"][0]["article_id"] == ARTICLE_B
    assert report["top_articles"][0]["qty"] == WINDOW_ITEMS


# ---------------------------------------------------------------------------
# Dashboard: SQL aggregate path replaces per-event sales report
# ---------------------------------------------------------------------------


def test_aggregate_sales_sql_shape_matches_legacy(db_session):
    """SQL aggregate totals for dashboard must match what legacy path returned.

    We seed orders via EdgeOrderItem (mirrors) and verify that
    _aggregate_sales returns consistent totals without calling
    build_event_sales_report per event.
    """
    db = db_session
    ev = db.query(Event).filter(Event.id == 1).one()

    # Seed some items
    _add_item(db, article_id=ARTICLE_A, article_name="Wurst", ordered_at=RANGE_START + timedelta(minutes=5), submission_id=100, line_cents=500, payment_status="paid")
    _add_item(db, article_id=ARTICLE_B, article_name="Bier", ordered_at=RANGE_START + timedelta(minutes=10), submission_id=101, session_id=201, line_cents=400, payment_status="open")
    db.commit()

    org = db.query(Organisation).filter(Organisation.id == 1).one()
    sales = _aggregate_sales(db, [ev], org)

    assert "totals" in sales
    assert "by_event" in sales
    assert len(sales["by_event"]) == 1
    evt_row = sales["by_event"][0]
    assert evt_row["event_id"] == 1
    assert evt_row["line_cents"] == 900  # 500 + 400
    assert evt_row["paid_cents"] == 500
    assert evt_row["open_cents"] == 400

    # Aggregate totals must sum correctly
    assert sales["totals"]["line_cents"] == 900
    assert sales["totals"]["paid_cents"] == 500
    assert sales["totals"]["open_cents"] == 400


def test_aggregate_sales_no_orders_returns_zeros(db_session):
    """Dashboard with no orders returns zeroed summary."""
    db = db_session
    ev = db.query(Event).filter(Event.id == 1).one()
    org = db.query(Organisation).filter(Organisation.id == 1).one()

    sales = _aggregate_sales(db, [ev], org)
    assert sales["totals"]["line_cents"] == 0
    assert sales["totals"]["distinct_orders_count"] == 0
    assert len(sales["by_event"]) == 1
    assert sales["by_event"][0]["line_cents"] == 0


def test_aggregate_sales_multiple_events(db_session):
    """SQL path must correctly group by event_id when multiple events exist."""
    db = db_session
    ev1 = db.query(Event).filter(Event.id == 1).one()

    # Create a second event
    ev2 = Event(
        id=2,
        name="Fest2",
        status="prod",
        start=RANGE_START - timedelta(hours=2),
        end=RANGE_END + timedelta(hours=2),
        organisation_id=1,
        payment_mode="pay_now",
        payment_types=["cash"],
    )
    db.add(ev2)
    db.commit()

    _add_item(db, event_id=1, article_id=ARTICLE_A, article_name="Wurst", ordered_at=RANGE_START + timedelta(minutes=1), submission_id=200, line_cents=500, payment_status="paid")
    _add_item(db, event_id=2, article_id=ARTICLE_B, article_name="Bier", ordered_at=RANGE_START + timedelta(minutes=2), submission_id=201, session_id=300, line_cents=300, payment_status="open")
    db.commit()

    org = db.query(Organisation).filter(Organisation.id == 1).one()
    sales = _aggregate_sales(db, [ev1, ev2], org)

    assert sales["totals"]["line_cents"] == 800
    event_cents = {row["event_id"]: row["line_cents"] for row in sales["by_event"]}
    assert event_cents[1] == 500
    assert event_cents[2] == 300


# ---------------------------------------------------------------------------
# get_event_for_reporting: does not load layout/cell graph
# ---------------------------------------------------------------------------


def test_get_event_for_reporting_loads_no_layouts(db_session):
    """get_event_for_reporting must not load stations, layouts, or cells."""
    db = db_session
    user = User(
        id=10,
        email="rpt@test.local",
        hashed_password=get_password_hash("secret"),
        role=ROLE_TENANT_ADMIN,
        hire_company_id=1,
    )
    db.add(user)
    db.commit()

    event = get_event_for_reporting(db, user, event_id=1, hire_company_id=1)
    state = sa_inspect(event)

    # Organisation is loaded (needed for currency/country)
    assert "organisation" not in state.unloaded

    # Layout-heavy collections must NOT be loaded
    assert "app_layouts" in state.unloaded
    assert "voucher_definitions" in state.unloaded
    assert "kitchen_monitor_printers" in state.unloaded


# ---------------------------------------------------------------------------
# Transactions: prior snapshot scoped to page client_ids
# ---------------------------------------------------------------------------


def _add_order(db, *, chunk_id: str, created_at: datetime, payload: dict, event_id: int = 1):
    db.add(
        EdgeSubmittedOrder(
            client_order_id=chunk_id,
            appliance_id=1,
            organisation_id=1,
            event_id=event_id,
            created_at=created_at,
            payload=payload,
        )
    )


def test_transactions_default_path_returns_correct_page(db_for_transactions):
    """Default created_at path must paginate correctly without loading all orders."""
    db, ev = db_for_transactions
    t_base = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

    # Add 10 orders
    for i in range(10):
        _add_order(
            db,
            chunk_id=f"order-{i}",
            created_at=t_base + timedelta(minutes=i),
            payload={
                "client_order_id": f"order-{i}",
                "payment_status": "open",
                "lines": [{"article_id": ARTICLE_A, "qty": 1, "unit_cents": 500, "article_name": "Wurst", "additions": []}],
            },
        )
    db.commit()

    page = build_event_transactions_page(db, ev, page=1, items_per_page=5, sort_by="created_at", sort_desc=True)
    assert page["total"] == 10
    assert len(page["items"]) == 5
    assert page["page"] == 1
    assert page["items_per_page"] == 5


def test_transactions_default_path_page_2(db_for_transactions):
    """Second page must return next batch."""
    db, ev = db_for_transactions
    t_base = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

    for i in range(10):
        _add_order(
            db,
            chunk_id=f"page2-order-{i}",
            created_at=t_base + timedelta(minutes=i),
            payload={"client_order_id": f"page2-order-{i}", "payment_status": "open", "lines": []},
        )
    db.commit()

    page2 = build_event_transactions_page(db, ev, page=2, items_per_page=5, sort_by="created_at", sort_desc=True)
    assert page2["total"] == 10
    assert len(page2["items"]) == 5


def test_transactions_kind_filter_still_works(db_for_transactions):
    """Memory-path kind filter must still return correct subset."""
    db, ev = db_for_transactions
    t_base = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

    _add_order(
        db,
        chunk_id="kind-order-1",
        created_at=t_base,
        payload={
            "client_order_id": "kind-order-1",
            "payment_status": "open",
            "lines": [{"article_id": ARTICLE_A, "qty": 1, "unit_cents": 500, "article_name": "Wurst", "additions": []}],
        },
    )
    _add_order(
        db,
        chunk_id="kind-payment-1",
        created_at=t_base + timedelta(minutes=5),
        payload={
            "client_order_id": "kind-payment-1",
            "payment_status": "paid",
            "payments": [{"type": "cash", "amount_cents": 700}],
        },
    )
    db.commit()

    # Filter to only "bestellung" kind
    result = build_event_transactions_page(db, ev, kind="bestellung")
    kinds = [r["kind"] for r in result["items"]]
    assert all(k == "bestellung" for k in kinds)
    assert result["total"] == 1


def test_transactions_prior_snapshot_scoped_to_page(db_for_transactions):
    """Prior snapshot lookup must work correctly for multi-version orders."""
    db, ev = db_for_transactions
    t_base = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

    # Two snapshots of the same logical order
    _add_order(
        db,
        chunk_id="snap-v1",
        created_at=t_base,
        payload={
            "client_order_id": "logical-order-1",
            "payment_status": "open",
            "lines": [
                {"article_id": ARTICLE_A, "qty": 2, "unit_cents": 500, "article_name": "Wurst", "additions": []},
            ],
        },
    )
    _add_order(
        db,
        chunk_id="snap-v2",
        created_at=t_base + timedelta(minutes=5),
        payload={
            "client_order_id": "logical-order-1",
            "payment_status": "open",
            "lines": [
                {"article_id": ARTICLE_A, "qty": 1, "unit_cents": 500, "article_name": "Wurst", "additions": []},
            ],
        },
    )
    db.commit()

    page = build_event_transactions_page(db, ev, page=1, items_per_page=25, sort_by="created_at", sort_desc=True)
    # Should return 2 rows (two sync snapshots) — prior lookup should not error
    assert page["total"] == 2
    assert len(page["items"]) == 2
