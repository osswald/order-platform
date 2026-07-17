"""Event transactions list (paginated Pi sync chunks)."""

from datetime import UTC, datetime

import pytest
from app.database import Base
from app.event_transactions import build_event_transactions_page
from app.models import (
    Appliance,
    EdgeSubmittedOrder,
    Event,
    EventWaiter,
    HireCompany,
    Organisation,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch_country_id = ensure_country(db, "CH", country_id=1)
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, hire_company_id=1, name="Org", country_id=ch_country_id, currency="CHF")
    db.add(org)
    now = datetime.now(UTC)
    ev = Event(
        id=1,
        name="Fest",
        status="prod",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
    )
    db.add(ev)
    db.add(EventWaiter(id=1, event_id=1, uuid="w-1", name="Anna", pin="1"))
    db.add(Appliance(id=1, hire_company_id=1, type="pi", name="Pi"))
    db.commit()
    yield db, ev
    db.close()


def _add_order(db, *, chunk_id, created_at, payload):
    db.add(
        EdgeSubmittedOrder(
            client_order_id=chunk_id,
            appliance_id=1,
            organisation_id=1,
            event_id=1,
            created_at=created_at,
            payload=payload,
        )
    )


def test_transactions_pagination_and_kinds(db_session):
    db, event = db_session
    t0 = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 6, 1, 11, 0, tzinfo=UTC)
    t2 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    _add_order(
        db,
        chunk_id="chunk-open",
        created_at=t0,
        payload={
            "client_order_id": "coll-1",
            "collective_bill_uuid": "cb-1",
            "payment_status": "open",
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": 2, "unit_cents": 500, "article_name": "Bier", "additions": []}],
        },
    )
    _add_order(
        db,
        chunk_id="chunk-partial",
        created_at=t1,
        payload={
            "client_order_id": "partial-coll-1",
            "collective_bill_uuid": "cb-1",
            "payment_status": "paid",
            "partial_settlement": True,
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": 1, "unit_cents": 500, "article_name": "Bier", "additions": []}],
            "payments": [{"type": "cash", "amount_cents": 500}],
        },
    )
    _add_order(
        db,
        chunk_id="chunk-paid-empty",
        created_at=t2,
        payload={
            "client_order_id": "coll-1",
            "payment_status": "paid",
            "payments": [{"type": "twint", "amount_cents": 500}],
            "lines": [],
        },
    )
    db.commit()

    page1 = build_event_transactions_page(db, event, page=1, items_per_page=2)
    assert page1["total"] == 3
    assert len(page1["items"]) == 2
    assert page1["items"][0]["kind"] == "zahlung"
    assert page1["items"][1]["kind"] == "teilzahlung"

    page2 = build_event_transactions_page(db, event, page=2, items_per_page=2)
    assert len(page2["items"]) == 1
    assert page2["items"][0]["kind"] == "bestellung"
    assert page2["items"][0]["line_count"] == 1
    assert len(page2["items"][0]["lines"]) == 1
    assert page2["items"][0]["lines"][0]["name"] == "Bier"
    assert page2["items"][0]["waiter_name"] == "Anna"


def test_transactions_filter_payment_status(db_session):
    db, event = db_session
    _add_order(
        db,
        chunk_id="a",
        created_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        payload={"client_order_id": "o1", "payment_status": "open", "lines": [{"article_id": 1, "qty": 1, "unit_cents": 100}]},
    )
    _add_order(
        db,
        chunk_id="b",
        created_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        payload={"client_order_id": "o2", "payment_status": "paid", "lines": [], "payments": [{"type": "cash", "amount_cents": 100}]},
    )
    db.commit()

    paid_only = build_event_transactions_page(db, event, payment_status="paid")
    assert paid_only["total"] == 1
    assert paid_only["items"][0]["kind"] == "zahlung"


def test_transactions_filter_kind(db_session):
    db, event = db_session
    _add_order(
        db,
        chunk_id="a",
        created_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        payload={"client_order_id": "o1", "payment_status": "open", "lines": [{"article_id": 1, "qty": 1, "unit_cents": 100}]},
    )
    _add_order(
        db,
        chunk_id="b",
        created_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        payload={
            "client_order_id": "o2",
            "payment_status": "paid",
            "partial_settlement": True,
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 100}],
            "payments": [{"type": "cash", "amount_cents": 100}],
        },
    )
    db.commit()

    partial = build_event_transactions_page(db, event, kind="teilzahlung")
    assert partial["total"] == 1
    assert partial["items"][0]["lines"]


def test_transactions_transfer_events(db_session):
    db, event = db_session
    _add_order(
        db,
        chunk_id="chunk-1",
        created_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        payload={
            "client_order_id": "table-5",
            "table_number": 5,
            "payment_status": "open",
            "lines": [{"article_id": 10, "qty": 1, "unit_cents": 500, "article_name": "Bier", "additions": []}],
            "transfer_events": [
                {
                    "to_table_number": 55,
                    "lines": [{"article_id": 10, "qty": 2, "unit_cents": 500, "article_name": "Bier", "additions": []}],
                }
            ],
        },
    )
    db.commit()

    page = build_event_transactions_page(db, event)
    row = page["items"][0]
    assert row["moved_line_cents"] == 1000
    assert len(row["moved_lines"]) == 1
    assert row["moved_lines"][0]["transfer_note"] == "Verschoben nach Tisch 55"
    assert row["moved_lines"][0]["name"] == "Bier"


def test_transactions_cash_drawer_kind(db_session):
    db, event = db_session
    _add_order(
        db,
        chunk_id="drawer-1",
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        payload={
            "entity_type": "cash_drawer",
            "opened_at": "2026-06-01T12:00:00+00:00",
            "cash_register_uuid": "reg-1",
            "cash_register_name": "Hauptkasse",
            "cash_drawer_command": "escp_pin2",
            "payment_id": 42,
            "client_order_id": "pwa-abc",
            "payments": [{"type": "cash", "amount_cents": 500}],
        },
    )
    db.commit()

    page = build_event_transactions_page(db, event, kind="kassenschublade")
    assert page["total"] == 1
    row = page["items"][0]
    assert row["kind"] == "kassenschublade"
    assert row["waiter_name"] == "Hauptkasse"
    assert row["paid_cents"] == 500
    assert "Beleg #42" in row["payment_methods"]


def test_transactions_sort_by_line_cents(db_session):
    db, event = db_session
    _add_order(
        db,
        chunk_id="a",
        created_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        payload={"client_order_id": "o1", "payment_status": "open", "lines": [{"article_id": 1, "qty": 1, "unit_cents": 100}]},
    )
    _add_order(
        db,
        chunk_id="b",
        created_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        payload={"client_order_id": "o2", "payment_status": "open", "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}]},
    )
    db.commit()

    asc = build_event_transactions_page(db, event, sort_by="line_cents", sort_desc=False)
    assert asc["items"][0]["line_cents"] == 100
    assert asc["items"][1]["line_cents"] == 500
