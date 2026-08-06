"""Per-event sparse article price overrides."""

from datetime import UTC, datetime

import pytest
from app.additions import replace_addition_links
from app.database import Base, SessionLocal
from app.event_copy import copy_event
from app.event_prices import (
    effective_article_price,
    load_price_map,
    upsert_price_overrides,
)
from app.main import app
from app.models import (
    Article,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventArticlePrice,
    EventArticleStock,
    EventStation,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from app.stock import article_snapshot_for_event
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import country_id_by_code, ensure_country

client = TestClient(app)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    ch_country_id = ensure_country(session, "CH", country_id=1)
    now = datetime.now(UTC)
    session.add_all(
        [
            HireCompany(id=1, name="HC"),
            Organisation(
                id=1,
                name="Org",
                country_id=ch_country_id,
                hire_company_id=1,
                currency="CHF",
                ingredients_enabled=False,
            ),
            ArticleCategory(id=1, name="Drinks", organisation_id=1),
            Article(
                id=10,
                name="Beer",
                label="B",
                price=5.0,
                article_category_id=1,
                is_addition=False,
            ),
            Article(
                id=11,
                name="Lime",
                label="L",
                price=0.5,
                article_category_id=1,
                is_addition=True,
            ),
            Article(
                id=12,
                name="Wine",
                label="W",
                price=8.0,
                article_category_id=1,
                is_addition=False,
            ),
            Event(
                id=1,
                name="Fest",
                status="config",
                start=now,
                end=now,
                organisation_id=1,
                payment_mode="pay_later",
                payment_types=["cash"],
            ),
        ]
    )
    session.flush()
    beer = session.query(Article).filter(Article.id == 10).one()
    lime = session.query(Article).filter(Article.id == 11).one()
    replace_addition_links(
        session,
        beer,
        [{"addition_article_id": lime.id, "sort_order": 0}],
    )
    st = EventStation(event_id=1, uuid="st-1", name="Bar", sort_order=0)
    st.articles = [beer, session.query(Article).filter(Article.id == 12).one()]
    session.add(st)
    lo = EventAppLayout(
        event_id=1,
        name="Main",
        is_default=True,
        grid_width=2,
        grid_height=2,
    )
    session.add(lo)
    session.flush()
    cell = EventAppLayoutCell(layout_id=lo.id, row=0, col=0, label="Beer", color="#fff")
    cell.articles = [beer]
    session.add(cell)
    session.commit()
    yield session
    session.close()


def test_upsert_and_clear_price_overrides(db):
    event = db.query(Event).filter(Event.id == 1).one()
    upsert_price_overrides(
        db,
        event,
        [
            {"article_id": 10, "price": 6.5},
            {"article_id": 11, "price": 1.0},
        ],
    )
    db.commit()

    price_map = load_price_map(db, event.id, {10, 11, 12})
    beer = db.query(Article).filter(Article.id == 10).one()
    lime = db.query(Article).filter(Article.id == 11).one()
    wine = db.query(Article).filter(Article.id == 12).one()
    assert effective_article_price(beer, price_map) == 6.5
    assert effective_article_price(lime, price_map) == 1.0
    assert effective_article_price(wine, price_map) == 8.0

    upsert_price_overrides(db, event, [{"article_id": 10, "price": None}])
    db.commit()
    price_map = load_price_map(db, event.id, {10, 11, 12})
    assert effective_article_price(beer, price_map) == 5.0
    assert db.query(EventArticlePrice).filter(
        EventArticlePrice.event_id == 1,
        EventArticlePrice.article_id == 10,
    ).count() == 0
    assert effective_article_price(lime, price_map) == 1.0


def test_article_snapshot_uses_effective_prices(db):
    event = db.query(Event).filter(Event.id == 1).one()
    upsert_price_overrides(
        db,
        event,
        [
            {"article_id": 10, "price": 6.5},
            {"article_id": 11, "price": 1.25},
        ],
    )
    db.commit()

    snap = article_snapshot_for_event(db, event)
    assert snap["10"]["price"] == 6.5
    assert snap["12"]["price"] == 8.0
    additions = snap["10"]["additions"]
    assert len(additions) == 1
    assert additions[0]["article_id"] == 11
    assert additions[0]["price"] == 1.25
    assert snap["11"]["price"] == 1.25


def test_copy_event_clones_price_overrides_and_skips_orphans(db):
    event = db.query(Event).filter(Event.id == 1).one()
    upsert_price_overrides(
        db,
        event,
        [
            {"article_id": 10, "price": 6.5},
            {"article_id": 11, "price": 1.0},
        ],
    )
    # Orphan: override for an article not on stations/layouts
    orphan = Article(
        id=99,
        name="Orphan",
        label="O",
        price=3.0,
        article_category_id=1,
        is_addition=False,
    )
    db.add(orphan)
    db.flush()
    db.add(EventArticlePrice(event_id=1, article_id=99, price=9.0))
    db.add(
        EventArticleStock(
            event_id=1,
            article_id=10,
            monitor_stock=True,
            in_stock=15,
            baseline_in_stock=15,
        )
    )
    db.commit()

    new_event = copy_event(db, event, name="Fest (Kopie)")
    db.commit()

    copied = {
        r.article_id: r.price
        for r in db.query(EventArticlePrice).filter(EventArticlePrice.event_id == new_event.id).all()
    }
    assert copied == {10: 6.5, 11: 1.0}
    assert 99 not in copied


def _seed_stock_price_admin():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Price Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Price Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="price-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
        )
        cat = ArticleCategory(name="Drinks", organisation_id=org.id)
        db.add(cat)
        db.flush()
        beer = Article(
            name="Beer",
            label="B",
            price=5.0,
            article_category_id=cat.id,
            is_addition=False,
        )
        lime = Article(
            name="Lime",
            label="L",
            price=0.5,
            article_category_id=cat.id,
            is_addition=True,
        )
        db.add_all([beer, lime])
        db.flush()
        replace_addition_links(
            db,
            beer,
            [{"addition_article_id": lime.id, "sort_order": 0}],
        )
        now = datetime.now(UTC)
        event = Event(
            name="Price Fest",
            status="config",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(event)
        db.flush()
        st = EventStation(event_id=event.id, uuid="st-price", name="Bar", sort_order=0)
        st.articles = [beer]
        db.add(st)
        lo = EventAppLayout(
            event_id=event.id,
            name="Main",
            is_default=True,
            grid_width=2,
            grid_height=2,
        )
        db.add(lo)
        db.flush()
        cell = EventAppLayoutCell(layout_id=lo.id, row=0, col=0, label="Beer", color="#fff")
        cell.articles = [beer]
        db.add(cell)
        db.commit()
        return event.id, beer.id, lime.id
    finally:
        db.close()


def _price_headers():
    token = client.post(
        "/auth/token",
        data={"username": "price-admin@test.local", "password": "secret"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_event_stock_api_org_price_and_override_roundtrip():
    event_id, beer_id, lime_id = _seed_stock_price_admin()
    headers = _price_headers()

    listed = client.get(f"/events/{event_id}/event-stock", headers=headers)
    assert listed.status_code == 200, listed.text
    items = {row["id"]: row for row in listed.json()["items"]}
    assert beer_id in items
    assert lime_id in items
    assert items[beer_id]["org_price"] == 5.0
    assert items[beer_id]["price"] is None
    assert items[lime_id]["org_price"] == 0.5
    assert items[lime_id]["price"] is None

    put = client.put(
        f"/events/{event_id}/event-stock",
        headers=headers,
        json={
            "items": [
                {
                    "article_id": beer_id,
                    "monitor_stock": False,
                    "price": 6.5,
                },
                {
                    "article_id": lime_id,
                    "monitor_stock": False,
                    "price": 1.0,
                },
            ]
        },
    )
    assert put.status_code == 200, put.text
    put_items = {row["id"]: row for row in put.json()["items"]}
    assert put_items[beer_id]["org_price"] == 5.0
    assert put_items[beer_id]["price"] == 6.5
    assert put_items[lime_id]["price"] == 1.0

    cleared = client.put(
        f"/events/{event_id}/event-stock",
        headers=headers,
        json={
            "items": [
                {
                    "article_id": beer_id,
                    "monitor_stock": False,
                    "price": None,
                },
                {
                    "article_id": lime_id,
                    "monitor_stock": False,
                    "price": 1.0,
                },
            ]
        },
    )
    assert cleared.status_code == 200, cleared.text
    cleared_items = {row["id"]: row for row in cleared.json()["items"]}
    assert cleared_items[beer_id]["price"] is None
    assert cleared_items[beer_id]["org_price"] == 5.0
    assert cleared_items[lime_id]["price"] == 1.0
