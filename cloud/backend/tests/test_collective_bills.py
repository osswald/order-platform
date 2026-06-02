"""Event collective bills upsert and list."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.event_collective_bills import build_event_collective_bills_list, upsert_collective_bill_from_payload
from app.event_sales import line_unit_cents
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
        "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500, "note": "", "additions": []}],
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

    paid_payload = {
        **payload,
        "payment_status": "paid",
        "settled_at": "2026-01-01T12:00:00+00:00",
        "payments": [{"type": "cash", "amount_cents": 500}],
    }
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
    closed = result2["collective_bills"][0]
    assert closed["status"] == "closed"
    assert len(closed["line_groups"]) >= 1
    assert closed["line_groups"][0]["total_qty"] >= 1
    assert closed["line_cents"] == 500
    assert closed["open_cents"] == 0
    assert closed["paid_cents"] == 500


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
    assert len(bill["line_groups"]) == 1
    assert bill["line_groups"][0]["total_qty"] == 2


def test_line_unit_cents_snapshotted_includes_additions(db_session):
    db, event = db_session
    arts = {1: {"price": 5.0, "name": "Bier", "additions": []}, 2: {"price": 1.0, "name": "Gross"}}
    line = {
        "article_id": 1,
        "qty": 1,
        "unit_cents": 1100,
        "additions": [{"article_id": 2, "qty": 1}],
    }
    assert line_unit_cents(line, arts) == 1100


def test_collective_bill_dedupes_stale_snapshots(db_session):
    """Only the latest sync snapshot per payload client_order_id counts toward totals."""
    db, event = db_session
    shared_uuid = "cb-familie"
    logical_cid = "coll-1-abc"
    older = EdgeSubmittedOrder(
        client_order_id="chunk-old",
        appliance_id=1,
        organisation_id=1,
        event_id=event.id,
        created_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        payload={
            "client_order_id": logical_cid,
            "collective_bill_uuid": shared_uuid,
            "collective_bill_name": "Familie",
            "payment_status": "open",
            "lines": [
                {"article_id": 10, "qty": 2, "unit_cents": 600, "article_name": "Bier", "additions": []},
                {"article_id": 11, "qty": 1, "unit_cents": 800, "article_name": "Schwein", "additions": []},
            ],
        },
    )
    newer = EdgeSubmittedOrder(
        client_order_id="chunk-new",
        appliance_id=1,
        organisation_id=1,
        event_id=event.id,
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        payload={
            "client_order_id": logical_cid,
            "collective_bill_uuid": shared_uuid,
            "collective_bill_name": "Familie",
            "payment_status": "open",
            "lines": [
                {"article_id": 10, "qty": 2, "unit_cents": 600, "article_name": "Bier", "additions": []},
                {"article_id": 11, "qty": 1, "unit_cents": 800, "article_name": "Schwein", "additions": []},
                {"article_id": 12, "qty": 5, "unit_cents": 1100, "article_name": "Kalbs", "additions": [{"article_id": 99, "qty": 1}]},
            ],
        },
    )
    db.add_all([older, newer])
    db.commit()

    bill = build_event_collective_bills_list(db, event)["collective_bills"][0]
    assert bill["line_cents"] == 7500
    assert len(bill["line_groups"]) == 3
    assert sum(g["line_total_cents"] for g in bill["line_groups"]) == 7500


def test_collective_bill_snapshotted_addon_not_double_priced(db_session):
    db, event = db_session
    cat = ArticleCategory(id=1, name="Food", organisation_id=1)
    db.add(cat)
    base = Article(id=3, name="Kalbsbratwurst", label="Kalbs", price=11.0, is_addition=False, article_category_id=1)
    extra = Article(id=99, name="mit Kartoffelsalat", label="Salat", price=3.0, is_addition=True, article_category_id=1)
    db.add_all([base, extra])
    db.add(ArticleAdditionLink(base_article_id=3, addition_article_id=99, sort_order=0))
    db.commit()

    payload = {
        "collective_bill_uuid": "cb-addon",
        "collective_bill_name": "Test",
        "payment_status": "open",
        "client_order_id": "coll-addon-1",
        "lines": [
            {
                "article_id": 3,
                "qty": 5,
                "unit_cents": 1100,
                "article_name": "Kalbsbratwurst",
                "additions": [{"article_id": 99, "qty": 1, "name": "mit Kartoffelsalat"}],
            }
        ],
    }
    db.add(
        EdgeSubmittedOrder(
            client_order_id="chunk-addon",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            payload=payload,
        )
    )
    db.commit()

    bill = next(b for b in build_event_collective_bills_list(db, event)["collective_bills"] if b["uuid"] == "cb-addon")
    assert bill["line_cents"] == 5500
    grp = bill["line_groups"][0]
    assert grp["line_total_cents"] == 5500
    assert bill["orders"][0]["lines"][0]["additions"][0]["line_cents"] == 0


def test_closed_collective_bill_shows_paid_positions(db_session):
    """Paid bill still lists allocated lines; totals split open vs paid."""
    db, event = db_session
    logical_cid = "coll-paid-1"
    bill_uuid = "cb-paid-pos"
    lines = [{"article_id": 1, "qty": 2, "unit_cents": 600, "article_name": "Bier", "additions": []}]
    db.add(
        EdgeSubmittedOrder(
            client_order_id="chunk-stale",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            created_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
            payload={
                "client_order_id": logical_cid,
                "collective_bill_uuid": bill_uuid,
                "collective_bill_name": "Familie",
                "payment_status": "open",
                "lines": lines,
            },
        )
    )
    db.add(
        EdgeSubmittedOrder(
            client_order_id="chunk-paid",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            created_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            payload={
                "client_order_id": logical_cid,
                "collective_bill_uuid": bill_uuid,
                "collective_bill_name": "Familie",
                "payment_status": "paid",
                "lines": lines,
                "payments": [{"type": "cash", "amount_cents": 1200}],
            },
        )
    )
    db.commit()

    bill = next(b for b in build_event_collective_bills_list(db, event)["collective_bills"] if b["uuid"] == bill_uuid)
    assert bill["status"] == "closed"
    assert len(bill["line_groups"]) == 1
    assert bill["line_cents"] == 1200
    assert bill["open_cents"] == 0
    assert bill["paid_cents"] == 1200


def test_partial_pay_merges_paid_and_open_allocations(db_session):
    db, event = db_session
    bill_uuid = "cb-partial"
    open_payload = {
        "client_order_id": "coll-open",
        "collective_bill_uuid": bill_uuid,
        "collective_bill_name": "Team",
        "payment_status": "open",
        "lines": [{"article_id": 10, "qty": 3, "unit_cents": 500, "article_name": "Bier", "additions": []}],
    }
    paid_payload = {
        "client_order_id": "partial-coll-1-xyz",
        "collective_bill_uuid": bill_uuid,
        "collective_bill_name": "Team",
        "payment_status": "paid",
        "partial_settlement": True,
        "lines": [{"article_id": 10, "qty": 2, "unit_cents": 500, "article_name": "Bier", "additions": []}],
        "payments": [{"type": "cash", "amount_cents": 1000}],
    }
    db.add_all(
        [
            EdgeSubmittedOrder(
                client_order_id="chunk-open",
                appliance_id=1,
                organisation_id=1,
                event_id=event.id,
                payload=open_payload,
            ),
            EdgeSubmittedOrder(
                client_order_id="chunk-partial",
                appliance_id=1,
                organisation_id=1,
                event_id=event.id,
                payload=paid_payload,
            ),
        ]
    )
    db.commit()

    bill = next(b for b in build_event_collective_bills_list(db, event)["collective_bills"] if b["uuid"] == bill_uuid)
    assert bill["line_groups"][0]["total_qty"] == 5
    assert bill["line_cents"] == 2500
    assert bill["open_cents"] == 1500
    assert bill["paid_cents"] == 1000

