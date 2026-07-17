"""Event stock initial (baseline) vs current (in_stock) separation."""

from datetime import UTC, datetime

import pytest
from app.ingredient_stock import upsert_ingredient_stock_rows
from app.models import (
    Article,
    ArticleCategory,
    ArticleIngredientLink,
    Event,
    EventArticleStock,
    EventIngredientStock,
    EventStation,
    HireCompany,
    Ingredient,
    Organisation,
)
from app.stock import apply_stock_deductions, upsert_stock_rows
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    from app.database import Base

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    ch_country_id = ensure_country(session, "CH", country_id=1)
    now = datetime.now(UTC)
    session.add(HireCompany(id=1, name="HC"))
    session.add(
        Organisation(
            id=1,
            name="Org",
            country_id=ch_country_id,
            hire_company_id=1,
            currency="CHF",
            ingredients_enabled=False,
        )
    )
    session.add(ArticleCategory(id=1, name="Food", organisation_id=1))
    art = Article(id=10, name="Burger", label="B", price=10.0, article_category_id=1)
    session.add(art)
    session.add(Ingredient(id=1, organisation_id=1, name="Beef", unit="kg"))
    event = Event(
        id=1,
        name="Fest",
        status="test",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
        payment_types=["cash"],
    )
    session.add(event)
    session.flush()
    st = EventStation(event_id=1, uuid="st-1", name="Grill", sort_order=0)
    st.articles = [art]
    session.add(st)
    session.add(
        EventArticleStock(
            event_id=1,
            article_id=10,
            monitor_stock=True,
            in_stock=73,
            baseline_in_stock=100,
        )
    )
    session.add(
        EventIngredientStock(
            event_id=1,
            ingredient_id=1,
            monitor_stock=True,
            in_stock=5,
            baseline_in_stock=10,
        )
    )
    session.commit()
    yield session
    session.close()


def test_upsert_current_only_preserves_baseline(db):
    event = db.query(Event).filter(Event.id == 1).first()
    upsert_stock_rows(
        db,
        event,
        [{"article_id": 10, "monitor_stock": True, "in_stock": 80}],
    )
    db.commit()
    row = db.query(EventArticleStock).filter(EventArticleStock.article_id == 10).one()
    assert row.in_stock == 80
    assert row.baseline_in_stock == 100


def test_upsert_initial_only_preserves_current(db):
    event = db.query(Event).filter(Event.id == 1).first()
    upsert_stock_rows(
        db,
        event,
        [{"article_id": 10, "monitor_stock": True, "initial_in_stock": 120}],
    )
    db.commit()
    row = db.query(EventArticleStock).filter(EventArticleStock.article_id == 10).one()
    assert row.in_stock == 73
    assert row.baseline_in_stock == 120


def test_upsert_both_updates_independently(db):
    event = db.query(Event).filter(Event.id == 1).first()
    upsert_stock_rows(
        db,
        event,
        [
            {
                "article_id": 10,
                "monitor_stock": True,
                "initial_in_stock": 200,
                "in_stock": 50,
            }
        ],
    )
    db.commit()
    row = db.query(EventArticleStock).filter(EventArticleStock.article_id == 10).one()
    assert row.in_stock == 50
    assert row.baseline_in_stock == 200


def test_upsert_ingredient_current_only_preserves_baseline(db):
    org = db.query(Organisation).filter(Organisation.id == 1).one()
    org.ingredients_enabled = True
    art = db.query(Article).filter(Article.id == 10).one()
    db.add(ArticleIngredientLink(base_article_id=art.id, ingredient_id=1, amount=1))
    db.commit()
    event = db.query(Event).filter(Event.id == 1).first()
    upsert_ingredient_stock_rows(
        db,
        event,
        [{"ingredient_id": 1, "monitor_stock": True, "in_stock": 7}],
    )
    db.commit()
    row = db.query(EventIngredientStock).filter(EventIngredientStock.ingredient_id == 1).one()
    assert float(row.in_stock) == 7
    assert float(row.baseline_in_stock) == 10


def test_apply_stock_deductions_only_touches_current(db):
    event = db.query(Event).filter(Event.id == 1).first()
    apply_stock_deductions(
        db,
        event.id,
        [{"article_id": 10, "qty": 3}],
        article_names={10: "Burger"},
    )
    db.commit()
    row = db.query(EventArticleStock).filter(EventArticleStock.article_id == 10).one()
    assert row.in_stock == 70
    assert row.baseline_in_stock == 100
