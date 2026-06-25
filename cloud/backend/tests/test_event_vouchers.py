"""Event voucher definitions and layout cell validation."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from tests.helpers import ensure_country
from app.event_config_validation import replace_event_configuration
from app.models import (
    Article,
    ArticleCategory,
    Event,
    EventAppLayoutCell,
    EventStation,
    EventVoucherDefinition,
    HireCompany,
    Organisation,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch_country_id = ensure_country(db, "CH", country_id=1)
    now = datetime.now(timezone.utc)
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF")
    db.add(org)
    cat = ArticleCategory(id=1, name="Drinks", organisation_id=1)
    db.add(cat)
    art = Article(id=10, name="Beer", label="B", price=5.0, article_category_id=1)
    db.add(art)
    ev = Event(
        id=1,
        name="Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
    )
    db.add(ev)
    st = EventStation(event_id=1, uuid="st-1", name="Bar", sort_order=0)
    db.add(st)
    db.flush()
    st.articles = [art]
    db.commit()
    yield db, ev, art
    db.close()


def test_replace_configuration_stores_vouchers_and_layout_cell(db_session):
    db, event, art = db_session
    vouchers_in = [
        SimpleNamespace(
            uuid="vd-amount",
            name="20 CHF",
            kind="fixed_amount",
            value_cents=2000,
            allowed_article_ids=[],
            include_additions=True,
        ),
    ]
    layouts_in = [
        SimpleNamespace(
            uuid="lo-1",
            name="Main",
            is_default=True,
            grid_width=1,
            grid_height=1,
            cells=[
                SimpleNamespace(
                    row=0,
                    col=0,
                    label="20.-",
                    color="#fff",
                    article_ids=[],
                    voucher_definition_uuid="vd-amount",
                )
            ],
        )
    ]
    replace_event_configuration(
        db,
        event,
        stations_in=[
            SimpleNamespace(
                uuid="st-1",
                name="Bar",
                printer_appliance_id=None,
                article_ids=[art.id],
                printer_rules=[],
            )
        ],
        event_waiters_in=[],
        app_layouts_in=layouts_in,
        cash_registers_in=[],
        voucher_definitions_in=vouchers_in,
    )
    db.commit()

    defs = db.query(EventVoucherDefinition).filter(EventVoucherDefinition.event_id == 1).all()
    assert len(defs) == 1
    assert defs[0].value_cents == 2000

    cell = db.query(EventAppLayoutCell).first()
    assert cell.voucher_definition_uuid == "vd-amount"
    assert cell.voucher_definition_uuids == ["vd-amount"]
    assert list(cell.articles) == []


def test_layout_cell_voucher_and_articles_combined(db_session):
    db, event, art = db_session
    vouchers_in = [
        SimpleNamespace(
            uuid="vd-amount",
            name="20 CHF",
            kind="fixed_amount",
            value_cents=2000,
            allowed_article_ids=[],
            include_additions=True,
        ),
    ]
    layouts_in = [
        SimpleNamespace(
            uuid="lo-1",
            name="Main",
            is_default=True,
            grid_width=1,
            grid_height=1,
            cells=[
                SimpleNamespace(
                    row=0,
                    col=0,
                    label="Combo",
                    color="#fff",
                    article_ids=[art.id],
                    voucher_definition_uuid="vd-amount",
                    voucher_definition_uuids=["vd-amount"],
                )
            ],
        )
    ]
    replace_event_configuration(
        db,
        event,
        stations_in=[
            SimpleNamespace(
                uuid="st-1",
                name="Bar",
                printer_appliance_id=None,
                article_ids=[art.id],
                printer_rules=[],
            )
        ],
        event_waiters_in=[],
        app_layouts_in=layouts_in,
        cash_registers_in=[],
        voucher_definitions_in=vouchers_in,
    )
    db.commit()
    cell = db.query(EventAppLayoutCell).first()
    assert cell.voucher_definition_uuids == ["vd-amount"]
    assert [a.id for a in cell.articles] == [art.id]


def test_layout_cell_multiple_vouchers(db_session):
    db, event, art = db_session
    vouchers_in = [
        SimpleNamespace(
            uuid="vd-10",
            name="10 CHF",
            kind="fixed_amount",
            value_cents=1000,
            allowed_article_ids=[],
            include_additions=True,
        ),
        SimpleNamespace(
            uuid="vd-20",
            name="20 CHF",
            kind="fixed_amount",
            value_cents=2000,
            allowed_article_ids=[],
            include_additions=True,
        ),
    ]
    layouts_in = [
        SimpleNamespace(
            uuid="lo-1",
            name="Main",
            is_default=True,
            grid_width=1,
            grid_height=1,
            cells=[
                SimpleNamespace(
                    row=0,
                    col=0,
                    label="Gutscheine",
                    color="#fff",
                    article_ids=[],
                    voucher_definition_uuid=None,
                    voucher_definition_uuids=["vd-10", "vd-20"],
                )
            ],
        )
    ]
    replace_event_configuration(
        db,
        event,
        stations_in=[
            SimpleNamespace(
                uuid="st-1",
                name="Bar",
                printer_appliance_id=None,
                article_ids=[art.id],
                printer_rules=[],
            )
        ],
        event_waiters_in=[],
        app_layouts_in=layouts_in,
        cash_registers_in=[],
        voucher_definitions_in=vouchers_in,
    )
    db.commit()
    cell = db.query(EventAppLayoutCell).first()
    assert cell.voucher_definition_uuids == ["vd-10", "vd-20"]
    assert cell.voucher_definition_uuid == "vd-10"


def test_replace_configuration_empty_cells_wipes_existing_layout_cells(db_session):
    """Full replace: saving a layout shell without cells deletes configured cells."""
    db, event, art = db_session
    layouts_with_cell = [
        SimpleNamespace(
            uuid="lo-1",
            name="Main",
            is_default=True,
            grid_width=1,
            grid_height=1,
            cells=[
                SimpleNamespace(
                    row=0,
                    col=0,
                    label="Beer",
                    color="#fff",
                    article_ids=[art.id],
                    voucher_definition_uuid=None,
                )
            ],
        )
    ]
    stations = [
        SimpleNamespace(
            uuid="st-1",
            name="Bar",
            printer_appliance_id=None,
            article_ids=[art.id],
            printer_rules=[],
        )
    ]
    replace_event_configuration(
        db,
        event,
        stations_in=stations,
        event_waiters_in=[],
        app_layouts_in=layouts_with_cell,
        cash_registers_in=[],
        voucher_definitions_in=[],
    )
    db.commit()
    assert db.query(EventAppLayoutCell).count() == 1

    layouts_empty_cells = [
        SimpleNamespace(
            uuid="lo-1",
            name="Main",
            is_default=True,
            grid_width=1,
            grid_height=1,
            cells=[],
        )
    ]
    replace_event_configuration(
        db,
        event,
        stations_in=stations,
        event_waiters_in=[],
        app_layouts_in=layouts_empty_cells,
        cash_registers_in=[],
        voucher_definitions_in=[],
    )
    db.commit()
    assert db.query(EventAppLayoutCell).count() == 0
