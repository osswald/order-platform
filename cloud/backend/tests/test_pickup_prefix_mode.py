"""Event pickup_prefix_mode: register vs station letter source."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.database import Base
from app.event_config_validation import replace_event_configuration
from app.event_copy import copy_event
from app.i18n.errors import api_error
from app.models import (
    Article,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventStation,
    HireCompany,
    Organisation,
)
from app.routers.edge import EdgeEventBundle
from app.routers.events_helpers import event_response, serialize_event_configuration
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

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
    db.add(Organisation(id=1, name="Org", country_id=ch_country_id, hire_company_id=1, currency="CHF"))
    db.add(ArticleCategory(id=1, name="Food", organisation_id=1))
    db.add(Article(id=10, name="Beer", label="B", price=5.0, article_category_id=1, is_addition=False))
    db.add(Article(id=11, name="Wine", label="W", price=6.0, article_category_id=1, is_addition=False))
    ev = Event(
        id=1,
        name="Fest",
        status="config",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
        payment_types=["cash"],
        cash_registers_enabled=True,
    )
    db.add(ev)
    db.commit()
    yield db, ev
    db.close()


def _layout(uuid: str = "layout-1"):
    return SimpleNamespace(
        uuid=uuid,
        name="Main",
        is_default=True,
        grid_width=2,
        grid_height=2,
        cells=[
            SimpleNamespace(
                row=0,
                col=0,
                label="Beer",
                color="#fff",
                article_ids=[10],
                voucher_definition_uuid=None,
                voucher_definition_uuids=[],
            )
        ],
    )


def _station(name: str, article_ids: list[int], prefix: str | None, uuid: str | None = None):
    return SimpleNamespace(
        uuid=uuid,
        name=name,
        printer_appliance_id=None,
        article_ids=article_ids,
        printer_rules=[],
        pickup_code_prefix=prefix,
    )


def _register(layout_uuid: str, prefix: str = "A"):
    return SimpleNamespace(
        uuid=None,
        name="Till",
        pickup_code_prefix=prefix,
        pin="0000",
        layout_uuid=layout_uuid,
        receipt_printer_appliance_id=None,
        cash_drawer_command="none",
        subsidiary_code=None,
        sumup_reader_id=None,
    )


def test_pickup_prefix_mode_defaults_to_register(db_session):
    db, ev = db_session
    db.refresh(ev)
    assert getattr(ev, "pickup_prefix_mode", "register") == "register"
    assert event_response(ev)["pickup_prefix_mode"] == "register"


def test_station_pickup_code_prefix_round_trips_in_configuration(db_session):
    db, ev = db_session
    replace_event_configuration(
        db,
        ev,
        stations_in=[_station("Grill", [10], "G")],
        event_waiters_in=[],
        app_layouts_in=[_layout()],
        cash_registers_in=[_register("layout-1")],
    )
    db.commit()
    db.refresh(ev)
    cfg = serialize_event_configuration(db, ev)
    assert cfg.stations[0].pickup_code_prefix == "G"


def test_station_mode_requires_unique_station_prefixes(db_session):
    db, ev = db_session
    ev.pickup_prefix_mode = "station"
    db.commit()
    layout = _layout()
    layout.cells.append(
        SimpleNamespace(
            row=0,
            col=1,
            label="Wine",
            color="#fff",
            article_ids=[11],
            voucher_definition_uuid=None,
            voucher_definition_uuids=[],
        )
    )
    with pytest.raises(HTTPException) as exc:
        replace_event_configuration(
            db,
            ev,
            stations_in=[
                _station("Grill", [10], "G"),
                _station("Bar", [11], "g"),
            ],
            event_waiters_in=[],
            app_layouts_in=[layout],
            cash_registers_in=[_register("layout-1")],
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "duplicate_station_pickup_prefix"


def test_station_mode_rejects_missing_station_prefix(db_session):
    db, ev = db_session
    ev.pickup_prefix_mode = "station"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        replace_event_configuration(
            db,
            ev,
            stations_in=[_station("Grill", [10], None)],
            event_waiters_in=[],
            app_layouts_in=[_layout()],
            cash_registers_in=[_register("layout-1")],
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "station_pickup_prefix_invalid"


def test_mode_lock_error_code_exists():
    err = api_error("pickup_prefix_mode_locked", 422)
    assert err.status_code == 422
    assert err.detail["code"] == "pickup_prefix_mode_locked"


def test_copy_event_copies_mode_and_station_prefixes(db_session):
    db, ev = db_session
    ev.pickup_prefix_mode = "station"
    db.commit()
    replace_event_configuration(
        db,
        ev,
        stations_in=[_station("Grill", [10], "G")],
        event_waiters_in=[],
        app_layouts_in=[_layout()],
        cash_registers_in=[_register("layout-1")],
    )
    db.commit()

    source = (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.stations).joinedload(EventStation.printer_rules),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells),
            joinedload(Event.cash_registers),
            joinedload(Event.voucher_definitions),
            joinedload(Event.kitchen_monitor_printers),
        )
        .filter(Event.id == ev.id)
        .one()
    )
    new_ev = copy_event(db, source, name="Fest Copy")
    db.commit()
    assert new_ev.pickup_prefix_mode == "station"
    assert {s.pickup_code_prefix for s in new_ev.stations} == {"G"}


def test_edge_event_bundle_includes_pickup_prefix_mode(db_session):
    db, ev = db_session
    ev.pickup_prefix_mode = "station"
    db.commit()
    db.refresh(ev)
    bundle = EdgeEventBundle(
        id=ev.id,
        name=ev.name,
        status=ev.status,
        currency="CHF",
        payment_mode="pay_later",
        payment_types=["cash"],
        shift_settlement_enabled=False,
        discounts_enabled=False,
        alternative_printers_enabled=False,
        kitchen_monitors_enabled=False,
        offer_payment_receipt=False,
        bluetooth_printing_enabled=False,
        pickup_prefix_mode=str(getattr(ev, "pickup_prefix_mode", None) or "register"),
        twint_qr_data_url=None,
        start=ev.start,
        end=ev.end,
        configuration={},
        articles={},
    )
    assert bundle.pickup_prefix_mode == "station"
