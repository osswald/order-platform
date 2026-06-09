"""Unit tests for event configuration validation helpers."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.event_config_validation import (
    assert_cell_articles_subset_of_stations,
    assert_exactly_one_default_layout,
    assert_layout_cells_within_grid,
    assert_source_waiter_in_org,
    assert_station_articles_in_org,
    article_ids_in_event_organisation,
    build_station_article_tree,
    station_article_union_from_payload,
)
from app.models import Article, ArticleCategory, Event, HireCompany, Organisation, Waiter
from app.routers.events import AppLayoutIn, LayoutCellIn, StationConfigIn


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            HireCompany(id=1, name="HC"),
            Organisation(id=1, name="Org", country="CH", hire_company_id=1),
            ArticleCategory(id=1, name="Food", organisation_id=1),
            Article(id=10, name="Beer", label="B", price=5.0, article_category_id=1, is_addition=False),
            Article(id=11, name="Cheese", label="C", price=2.0, article_category_id=1, is_addition=True),
            Waiter(id=1, name="Max", organisation_id=1),
            Event(
                id=1,
                name="Fest",
                status="config",
                start=now,
                end=now,
                currency="CHF",
                organisation_id=1,
                payment_mode="pay_later",
                payment_types=["cash"],
            ),
        ]
    )
    session.commit()
    yield session
    session.close()


def test_article_ids_in_event_organisation(db):
    event = db.query(Event).filter(Event.id == 1).first()
    assert article_ids_in_event_organisation(db, event, [10]) is True
    assert article_ids_in_event_organisation(db, event, [99]) is False


def test_assert_station_articles_rejects_addition(db):
    event = db.query(Event).filter(Event.id == 1).first()
    with pytest.raises(HTTPException) as exc:
        assert_station_articles_in_org(db, event, [11])
    assert exc.value.status_code == 422


def test_station_article_union_and_cell_subset(db):
    stations = [StationConfigIn(name="Bar", article_ids=[10])]
    layouts = [
        AppLayoutIn(
            is_default=True,
            grid_width=2,
            grid_height=2,
            cells=[LayoutCellIn(row=0, col=0, article_ids=[10])],
        )
    ]
    assert station_article_union_from_payload(stations) == {10}
    assert_cell_articles_subset_of_stations(stations, layouts)


def test_cell_article_not_on_station_raises(db):
    stations = [StationConfigIn(name="Bar", article_ids=[10])]
    layouts = [
        AppLayoutIn(
            is_default=True,
            grid_width=2,
            grid_height=2,
            cells=[LayoutCellIn(row=0, col=0, article_ids=[99])],
        )
    ]
    with pytest.raises(HTTPException) as exc:
        assert_cell_articles_subset_of_stations(stations, layouts)
    assert exc.value.detail["code"] == "validation_failed"


def test_assert_source_waiter_in_org(db):
    event = db.query(Event).filter(Event.id == 1).first()
    assert_source_waiter_in_org(db, event, 1)
    with pytest.raises(HTTPException):
        assert_source_waiter_in_org(db, event, 999)


def test_assert_exactly_one_default_layout():
    with pytest.raises(HTTPException):
        assert_exactly_one_default_layout([])
    with pytest.raises(HTTPException):
        assert_exactly_one_default_layout(
            [
                AppLayoutIn(is_default=True, grid_width=1, grid_height=1),
                AppLayoutIn(is_default=True, grid_width=1, grid_height=1),
            ]
        )
    assert_exactly_one_default_layout(
        [AppLayoutIn(is_default=True, grid_width=2, grid_height=2, cells=[])]
    )


def test_assert_layout_cells_within_grid():
    with pytest.raises(HTTPException):
        assert_layout_cells_within_grid(
            [
                AppLayoutIn(
                    is_default=True,
                    grid_width=1,
                    grid_height=1,
                    cells=[LayoutCellIn(row=1, col=0)],
                )
            ]
        )
    with pytest.raises(HTTPException):
        assert_layout_cells_within_grid(
            [
                AppLayoutIn(
                    is_default=True,
                    grid_width=2,
                    grid_height=1,
                    cells=[LayoutCellIn(row=0, col=0), LayoutCellIn(row=0, col=0)],
                )
            ]
        )


def test_build_station_article_tree_empty_without_stations(db):
    from app.models import EventStation

    event = db.query(Event).filter(Event.id == 1).first()
    assert build_station_article_tree(db, event) == []
    st = EventStation(event_id=1, uuid="st-1", name="Bar", sort_order=0)
    st.articles = [db.query(Article).filter(Article.id == 10).first()]
    db.add(st)
    db.commit()
    db.refresh(event)
    tree = build_station_article_tree(db, event)
    assert len(tree) == 1
    assert tree[0]["key"] == "cat-1"
    assert any(c["data"]["article_id"] == 10 for c in tree[0]["children"])
