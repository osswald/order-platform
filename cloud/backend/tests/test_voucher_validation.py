"""Unit tests for voucher definition validation."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.database import Base
from app.models import Article, ArticleCategory, Event, HireCompany, Organisation
from app.vouchers import (
    VOUCHER_KIND_ARTICLE,
    VOUCHER_KIND_FIXED,
    assert_voucher_articles_in_org,
    assert_voucher_definition_in,
    normalize_cell_voucher_uuids,
)
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
            Article(id=10, name="Beer", label="B", price=5.0, article_category_id=1, is_addition=False),
            Article(id=11, name="Extra", label="E", price=1.0, article_category_id=1, is_addition=True),
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


def test_assert_voucher_definition_in_fixed_amount(db):
    event = db.query(Event).filter(Event.id == 1).first()
    vd = SimpleNamespace(kind=VOUCHER_KIND_FIXED, name="CHF 10", value_cents=1000)
    assert_voucher_definition_in(event, vd)
    with pytest.raises(HTTPException):
        assert_voucher_definition_in(event, SimpleNamespace(kind=VOUCHER_KIND_FIXED, name="X", value_cents=0))


def test_assert_voucher_definition_in_article_entitlement(db):
    event = db.query(Event).filter(Event.id == 1).first()
    vd = SimpleNamespace(
        kind=VOUCHER_KIND_ARTICLE,
        name="Free beer",
        allowed_article_ids=[10],
    )
    assert_voucher_definition_in(event, vd)
    with pytest.raises(HTTPException):
        assert_voucher_definition_in(
            event, SimpleNamespace(kind=VOUCHER_KIND_ARTICLE, name="X", allowed_article_ids=[])
        )


def test_assert_voucher_articles_in_org(db):
    event = db.query(Event).filter(Event.id == 1).first()
    assert_voucher_articles_in_org(db, event, [10])
    with pytest.raises(HTTPException):
        assert_voucher_articles_in_org(db, event, [11])
    with pytest.raises(HTTPException):
        assert_voucher_articles_in_org(db, event, [99])


def test_normalize_cell_voucher_uuids_dedupes_legacy():
    cell = SimpleNamespace(
        voucher_definition_uuids=["uuid-a", "uuid-b"],
        voucher_definition_uuid="uuid-a",
    )
    assert normalize_cell_voucher_uuids(cell) == ["uuid-a", "uuid-b"]
