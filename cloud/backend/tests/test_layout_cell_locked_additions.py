"""Layout cell locked_addition_ids persistence and validation."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.database import Base
from app.event_config_validation import replace_event_configuration
from app.i18n.errors import detail_message
from app.models import (
    Article,
    ArticleAdditionLink,
    ArticleCategory,
    Event,
    EventAppLayoutCell,
    EventStation,
    HireCompany,
    Organisation,
)
from app.routers.events_helpers import serialize_event_configuration
from app.schemas.events import AppLayoutIn, LayoutCellIn
from fastapi import HTTPException
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
    now = datetime.now(UTC)
    db.add(HireCompany(id=1, name="HC"))
    db.add(
        Organisation(
            id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF"
        )
    )
    db.add(ArticleCategory(id=1, name="Drinks", organisation_id=1))
    base = Article(id=10, name="Gin Tonic", label="GT", price=12.0, article_category_id=1)
    lime = Article(id=11, name="Lime", label="L", price=0.5, article_category_id=1, is_addition=True)
    ice = Article(id=12, name="Ice", label="Ice", price=0.0, article_category_id=1, is_addition=True)
    cola = Article(id=13, name="Cola", label="C", price=4.0, article_category_id=1)
    db.add_all([base, lime, ice, cola])
    db.add(
        Event(
            id=1,
            name="Fest",
            status="config",
            start=now,
            end=now,
            organisation_id=1,
        )
    )
    st = EventStation(event_id=1, uuid="st-1", name="Bar", sort_order=0)
    db.add(st)
    db.flush()
    st.articles = [base, cola]
    db.add(
        ArticleAdditionLink(
            base_article_id=10, addition_article_id=11, sort_order=0, preselected=False
        )
    )
    db.add(
        ArticleAdditionLink(
            base_article_id=10, addition_article_id=12, sort_order=1, preselected=False
        )
    )
    db.commit()
    yield db
    db.close()


def _station_in():
    return SimpleNamespace(
        uuid="st-1",
        name="Bar",
        printer_appliance_id=None,
        article_ids=[10, 13],
        printer_rules=[],
    )


def _layout_in(*, article_ids, locked_addition_ids=None, voucher_uuid=None, voucher_uuids=None):
    return SimpleNamespace(
        uuid="lo-1",
        name="Main",
        is_default=True,
        grid_width=2,
        grid_height=2,
        cells=[
            SimpleNamespace(
                row=0,
                col=0,
                label="GT+L",
                color="#fff",
                article_ids=article_ids,
                voucher_definition_uuid=voucher_uuid,
                voucher_definition_uuids=voucher_uuids
                if voucher_uuids is not None
                else ([voucher_uuid] if voucher_uuid else []),
                locked_addition_ids=locked_addition_ids or [],
            )
        ],
    )


def test_replace_persists_locked_addition_ids_in_order(db_session):
    db = db_session
    replace_event_configuration(
        db,
        db.get(Event, 1),
        stations_in=[_station_in()],
        event_waiters_in=[],
        app_layouts_in=[_layout_in(article_ids=[10], locked_addition_ids=[12, 11])],
        cash_registers_in=[],
        voucher_definitions_in=[],
    )
    db.commit()

    cell = db.query(EventAppLayoutCell).one()
    assert [a.id for a in cell.articles] == [10]
    assert [link.article_id for link in cell.locked_addition_links] == [12, 11]

    cfg = serialize_event_configuration(db, db.get(Event, 1), include_layout_cells=True)
    assert cfg.app_layouts[0].cells[0].locked_addition_ids == [12, 11]


def test_locked_additions_rejected_with_multiple_articles(db_session):
    db = db_session
    with pytest.raises(HTTPException) as exc:
        replace_event_configuration(
            db,
            db.get(Event, 1),
            stations_in=[_station_in()],
            event_waiters_in=[],
            app_layouts_in=[_layout_in(article_ids=[10, 13], locked_addition_ids=[11])],
            cash_registers_in=[],
            voucher_definitions_in=[],
        )
    assert exc.value.status_code == 422
    msg = detail_message(exc.value.detail).lower()
    assert "gesperrte" in msg or "locked" in msg or "zusatz" in msg or "addition" in msg


def test_locked_additions_rejected_with_voucher(db_session):
    db = db_session
    vouchers_in = [
        SimpleNamespace(
            uuid="vd-1",
            name="20 CHF",
            kind="fixed_amount",
            value_cents=2000,
            allowed_article_ids=[],
            include_additions=True,
        )
    ]
    with pytest.raises(HTTPException) as exc:
        replace_event_configuration(
            db,
            db.get(Event, 1),
            stations_in=[_station_in()],
            event_waiters_in=[],
            app_layouts_in=[
                _layout_in(
                    article_ids=[10],
                    locked_addition_ids=[11],
                    voucher_uuid="vd-1",
                    voucher_uuids=["vd-1"],
                )
            ],
            cash_registers_in=[],
            voucher_definitions_in=vouchers_in,
        )
    assert exc.value.status_code == 422


def test_locked_addition_must_be_linked_to_base(db_session):
    db = db_session
    orphan = Article(
        id=99,
        name="Orphan Zusatz",
        label="O",
        price=1.0,
        article_category_id=1,
        is_addition=True,
    )
    db.add(orphan)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        replace_event_configuration(
            db,
            db.get(Event, 1),
            stations_in=[_station_in()],
            event_waiters_in=[],
            app_layouts_in=[_layout_in(article_ids=[10], locked_addition_ids=[99])],
            cash_registers_in=[],
            voucher_definitions_in=[],
        )
    assert exc.value.status_code == 422


def test_schema_accepts_locked_addition_ids_field():
    cell = LayoutCellIn(row=0, col=0, article_ids=[10], locked_addition_ids=[11, 12])
    assert cell.locked_addition_ids == [11, 12]
    layout = AppLayoutIn(is_default=True, grid_width=1, grid_height=1, cells=[cell])
    assert layout.cells[0].locked_addition_ids == [11, 12]


def test_classic_cell_defaults_empty_locked_addition_ids(db_session):
    db = db_session
    replace_event_configuration(
        db,
        db.get(Event, 1),
        stations_in=[_station_in()],
        event_waiters_in=[],
        app_layouts_in=[_layout_in(article_ids=[10, 13])],
        cash_registers_in=[],
        voucher_definitions_in=[],
    )
    db.commit()
    cfg = serialize_event_configuration(db, db.get(Event, 1), include_layout_cells=True)
    assert cfg.app_layouts[0].cells[0].locked_addition_ids == []
