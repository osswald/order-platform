"""Event collective bills upsert and list."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.event_collective_bills import build_event_collective_bills_list, upsert_collective_bill_from_payload
from app.models import (
    Appliance,
    Article,
    ArticleAdditionLink,
    ArticleCategory,
    EdgeSubmittedOrder,
    Event,
    EventCollectiveBill,
    HireCompany,
    Organisation,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, hire_company_id=1, name="Org", country="CH")
    db.add(org)
    now = datetime.now(timezone.utc)
    ev = Event(
        id=1,
        name="Fest",
        status="active",
        start=now,
        end=now,
        organisation_id=1,
        currency="CHF",
        payment_mode="pay_later",
    )
    db.add(ev)
    app = Appliance(id=1, hire_company_id=1, type="pi", name="Pi")
    db.add(app)
    db.commit()
    yield db, ev
    db.close()


def test_upsert_and_list_collective_bills(db_session):
    db, event = db_session
    payload = {
        "collective_bill_uuid": "cb-uuid-1",
        "collective_bill_name": "Personal",
        "table_number": None,
        "payment_status": "open",
        "lines": [{"article_id": 1, "qty": 1, "note": "", "additions": []}],
    }
    upsert_collective_bill_from_payload(
        db, event_id=event.id, appliance_id=1, payload=payload
    )
    db.add(
        EdgeSubmittedOrder(
            client_order_id="order-1",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            payload=payload,
        )
    )
    db.commit()

    result = build_event_collective_bills_list(db, event)
    assert len(result["collective_bills"]) == 1
    bill = result["collective_bills"][0]
    assert bill["uuid"] == "cb-uuid-1"
    assert bill["name"] == "Personal"
    assert bill["status"] == "open"
    assert bill["order_count"] == 1

    paid_payload = {**payload, "payment_status": "paid", "settled_at": "2026-01-01T12:00:00+00:00"}
    upsert_collective_bill_from_payload(
        db, event_id=event.id, appliance_id=1, payload=paid_payload
    )
    order_row = db.query(EdgeSubmittedOrder).filter(EdgeSubmittedOrder.client_order_id == "order-1").first()
    order_row.payload = paid_payload
    upsert_collective_bill_from_payload(
        db, event_id=event.id, appliance_id=1, payload=paid_payload
    )
    db.commit()
    header = db.query(EventCollectiveBill).filter(EventCollectiveBill.uuid == "cb-uuid-1").first()
    assert header.closed_at is not None
    result2 = build_event_collective_bills_list(db, event)
    assert result2["collective_bills"][0]["status"] == "closed"


def test_list_collective_bills_with_article_additions(db_session):
    """Regression: base article with linked Zusatz must not mutate arts dict during iteration."""
    db, event = db_session
    cat = ArticleCategory(id=1, name="Getränke", organisation_id=1)
    db.add(cat)
    base = Article(
        id=1,
        name="Bier",
        label="Bier",
        price=5.0,
        is_addition=False,
        article_category_id=1,
    )
    extra = Article(
        id=2,
        name="Gross",
        label="Gross",
        price=1.0,
        is_addition=True,
        article_category_id=1,
    )
    db.add_all([base, extra])
    db.add(ArticleAdditionLink(base_article_id=1, addition_article_id=2, sort_order=0))
    db.commit()

    payload = {
        "collective_bill_uuid": "cb-additions",
        "collective_bill_name": "VIP",
        "payment_status": "open",
        "lines": [
            {
                "article_id": 1,
                "qty": 1,
                "note": "",
                "additions": [{"article_id": 2, "qty": 1}],
            }
        ],
    }
    db.add(
        EdgeSubmittedOrder(
            client_order_id="order-add",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            payload=payload,
        )
    )
    db.commit()

    result = build_event_collective_bills_list(db, event)
    bill = next(b for b in result["collective_bills"] if b["uuid"] == "cb-additions")
    assert bill["line_cents"] == 600
    assert bill["orders"][0]["lines"][0]["name"] == "Bier"
    assert bill["orders"][0]["lines"][0]["additions"][0]["name"] == "Gross"


def test_collective_bill_order_count_distinct_order_numbers(db_session):
    db, event = db_session
    shared = {
        "collective_bill_uuid": "cb-shared",
        "collective_bill_name": "Team",
        "payment_status": "open",
        "order_number": 42,
        "ordered_at": "2026-05-20T12:00:00+00:00",
        "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500, "article_name": "Bier", "additions": []}],
    }
    for i, cid in enumerate(["sync-a", "sync-b"], start=1):
        db.add(
            EdgeSubmittedOrder(
                client_order_id=cid,
                appliance_id=1,
                organisation_id=1,
                event_id=event.id,
                payload={**shared, "client_order_id": cid},
            )
        )
    db.commit()

    result = build_event_collective_bills_list(db, event)
    bill = next(b for b in result["collective_bills"] if b["uuid"] == "cb-shared")
    assert bill["order_count"] == 1
    assert len(bill["orders"]) == 2
    assert bill["orders"][0]["order_number"] == 42

