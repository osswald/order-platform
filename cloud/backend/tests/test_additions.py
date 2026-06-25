"""Unit tests for article addition helpers."""

from datetime import UTC, datetime

import pytest
from app.additions import (
    addition_delta_cents,
    build_additions_for_base,
    load_links_for_bases,
    replace_addition_links,
    serialize_links_for_admin,
    validate_base_article,
)
from app.database import Base
from app.models import Article, ArticleCategory, Event, HireCompany, Organisation
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


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
            Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF"),
            ArticleCategory(id=1, name="Food", organisation_id=1),
            Article(id=10, name="Beer", label="B", price=5.5, article_category_id=1, is_addition=False),
            Article(id=11, name="Lime", label="L", price=0.5, article_category_id=1, is_addition=True),
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
    session.commit()
    yield session
    session.close()


def test_addition_delta_cents(db):
    art = db.query(Article).filter(Article.id == 10).first()
    assert addition_delta_cents(art) == 550


def test_load_and_replace_addition_links(db):
    base = db.query(Article).filter(Article.id == 10).first()
    add = db.query(Article).filter(Article.id == 11).first()
    links = replace_addition_links(
        db,
        base,
        [{"addition_article_id": add.id, "sort_order": 0}],
    )
    db.commit()
    assert len(links) == 1
    loaded = load_links_for_bases(db, {base.id})
    assert loaded[base.id][0].addition_article_id == add.id


def test_validate_base_article_rejects_addition(db):
    with pytest.raises(HTTPException) as exc:
        validate_base_article(db, 11)
    assert exc.value.status_code == 400


def test_replace_addition_links_persists_preselected(db):
    base = db.query(Article).filter(Article.id == 10).first()
    add = db.query(Article).filter(Article.id == 11).first()
    links = replace_addition_links(
        db,
        base,
        [{"addition_article_id": add.id, "sort_order": 0, "preselected": True}],
    )
    db.commit()
    assert links[0].preselected is True


def test_replace_addition_links_defaults_preselected_false(db):
    base = db.query(Article).filter(Article.id == 10).first()
    add = db.query(Article).filter(Article.id == 11).first()
    links = replace_addition_links(
        db,
        base,
        [{"addition_article_id": add.id, "sort_order": 0}],
    )
    db.commit()
    assert links[0].preselected is False


def test_serialize_links_for_admin_includes_preselected(db):
    base = db.query(Article).filter(Article.id == 10).first()
    add = db.query(Article).filter(Article.id == 11).first()
    replace_addition_links(
        db,
        base,
        [{"addition_article_id": add.id, "sort_order": 0, "preselected": True}],
    )
    db.commit()
    items = serialize_links_for_admin(db, base)
    assert len(items) == 1
    assert items[0]["preselected"] is True


def test_build_additions_for_base_includes_preselected(db):
    base = db.query(Article).filter(Article.id == 10).first()
    add = db.query(Article).filter(Article.id == 11).first()
    links = replace_addition_links(
        db,
        base,
        [{"addition_article_id": add.id, "sort_order": 0, "preselected": True}],
    )
    db.commit()
    arts = {a.id: a for a in db.query(Article).all()}
    built = build_additions_for_base(links, arts, {})
    assert built[0]["preselected"] is True
