"""Event configuration load performance: selectinload and API contracts."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.database import Base, SessionLocal
from app.main import app
from app.models import (
    Article,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventCashRegister,
    EventStation,
    EventVoucherDefinition,
    EventWaiter,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.routers.events_helpers import (
    event_configuration_load_options,
    get_event_for_configuration,
    serialize_event_configuration,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

from tests.helpers import country_id_by_code, ensure_country

client = TestClient(app)


@pytest.fixture
def config_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch = ensure_country(db, "CH", country_id=1)
    now = datetime.now(UTC)
    db.add_all(
        [
            HireCompany(id=1, name="HC"),
            Organisation(id=1, name="Org", country_id=ch, hire_company_id=1, currency="CHF"),
            ArticleCategory(id=1, name="Food", organisation_id=1),
            Article(id=10, name="Bratwurst", label="BW", price=8.0, article_category_id=1),
            Article(id=11, name="Beer", label="B", price=5.0, article_category_id=1),
            User(
                id=1,
                email="cfg@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=1,
            ),
            Event(
                id=1,
                name="Fest",
                status="config",
                start=now,
                end=now,
                organisation_id=1,
                payment_mode="pay_later",
                vouchers_enabled=True,
            ),
        ]
    )
    db.flush()
    st = EventStation(event_id=1, uuid="st-1", name="Grill", sort_order=0)
    db.add(st)
    db.flush()
    st.articles = [db.get(Article, 10), db.get(Article, 11)]
    ew = EventWaiter(event_id=1, uuid="ew-1", name="Max", pin="0000", source_waiter_id=None)
    db.add(ew)
    layout = EventAppLayout(
        event_id=1,
        uuid="lo-1",
        name="Main",
        is_default=True,
        grid_width=2,
        grid_height=2,
    )
    db.add(layout)
    db.flush()
    cell = EventAppLayoutCell(
        layout_id=layout.id,
        row=0,
        col=0,
        label="BW",
        color="#E3C638",
    )
    db.add(cell)
    db.flush()
    cell.articles = [db.get(Article, 10)]
    db.add(
        EventVoucherDefinition(
            event_id=1,
            uuid="vd-1",
            name="Essen",
            kind="article_entitlement",
            value_cents=None,
            allowed_article_ids=[10],
            include_additions=True,
            sort_order=0,
        )
    )
    db.add(
        EventCashRegister(
            event_id=1,
            uuid="reg-1",
            name="Kasse 1",
            sort_order=0,
            pickup_code_prefix="A",
            pin="0000",
            layout_uuid="lo-1",
        )
    )
    db.commit()
    user = db.get(User, 1)
    yield db, user
    db.close()


def test_configuration_load_options_use_selectinload_for_collections():
    opts_full = event_configuration_load_options(include_layout_cells=True)
    opts_summary = event_configuration_load_options(include_layout_cells=False)

    def strategies(options):
        out = []
        for opt in options:
            for attr in opt.context:
                out.append(attr.strategy)
        return out

    full_strats = strategies(opts_full)
    summary_strats = strategies(opts_summary)
    assert (("lazy", "joined"),) in full_strats  # organisation many-to-one
    assert all(
        s == (("lazy", "joined"),) or s == (("lazy", "selectin"),) for s in full_strats
    )
    # Collections must not use joined loading
    collection_strats = [s for s in full_strats if s != (("lazy", "joined"),)]
    assert collection_strats
    assert all(s == (("lazy", "selectin"),) for s in collection_strats)
    assert all(s == (("lazy", "selectin"),) or s == (("lazy", "joined"),) for s in summary_strats)
    assert (("lazy", "selectin"),) in summary_strats


def test_get_event_for_configuration_loads_multi_collections(config_db):
    db, user = config_db
    event = get_event_for_configuration(db, user, 1, hire_company_id=1, include_layout_cells=True)
    assert len(event.stations) == 1
    assert {a.id for a in event.stations[0].articles} == {10, 11}
    assert len(event.event_waiters) == 1
    assert len(event.app_layouts) == 1
    layout = event.app_layouts[0]
    assert len(layout.cells) == 1
    assert [a.id for a in layout.cells[0].articles] == [10]
    assert len(event.voucher_definitions) == 1
    assert len(event.cash_registers) == 1

    # Relationships usable after expire without lazy IO if selectinloaded
    db.expire_all()
    event = get_event_for_configuration(db, user, 1, hire_company_id=1, include_layout_cells=True)
    state = sa_inspect(event)
    assert not state.unloaded.intersection(
        {"stations", "event_waiters", "app_layouts", "cash_registers", "voucher_definitions"}
    )

    cfg = serialize_event_configuration(db, event, include_layout_cells=True)
    assert set(cfg.stations[0].article_ids) == {10, 11}
    assert cfg.app_layouts[0].cells[0].article_ids == [10]
    assert cfg.app_layouts[0].cells[0].label == "BW"


def test_get_event_for_configuration_summary_skips_cells(config_db):
    db, user = config_db
    event = get_event_for_configuration(db, user, 1, hire_company_id=1, include_layout_cells=False)
    cfg = serialize_event_configuration(db, event, include_layout_cells=False)
    assert cfg.stations[0].article_ids
    assert cfg.app_layouts[0].cells == []


def _api_seed():
    db = SessionLocal()
    try:
        suffix = uuid4().hex[:8]
        hc = HireCompany(name=f"Cfg HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Cfg Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        user = User(
            email=f"cfg-api-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc.id,
        )
        cat = ArticleCategory(name="Food", organisation_id=org.id)
        db.add_all([user, cat])
        db.flush()
        art = Article(name="Cola", label="C", price=3.0, article_category_id=cat.id)
        db.add(art)
        db.flush()
        now = datetime.now(UTC)
        event = Event(
            name=f"Cfg Event {suffix}",
            status="config",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_mode="pay_later",
        )
        db.add(event)
        db.flush()
        st = EventStation(event_id=event.id, uuid=str(uuid4()), name="Bar", sort_order=0)
        db.add(st)
        db.flush()
        st.articles = [art]
        layout_uuid = str(uuid4())
        layout = EventAppLayout(
            event_id=event.id,
            uuid=layout_uuid,
            name="Standard",
            is_default=True,
            grid_width=2,
            grid_height=2,
        )
        db.add(layout)
        db.flush()
        cell = EventAppLayoutCell(layout_id=layout.id, row=0, col=0, label="Cola", color="#317EE3")
        db.add(cell)
        db.flush()
        cell.articles = [art]
        db.commit()
        return event.id, art.id, layout_uuid, st.uuid, user.email
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_configuration_api_get_full_and_summary():
    event_id, art_id, layout_uuid, _st_uuid, email = _api_seed()
    token = _token(email)
    headers = {"Authorization": f"Bearer {token}"}

    full = client.get(f"/events/{event_id}/configuration", headers=headers)
    assert full.status_code == 200, full.text
    body = full.json()
    assert body["stations"][0]["article_ids"] == [art_id]
    assert body["app_layouts"][0]["uuid"] == layout_uuid
    assert body["app_layouts"][0]["cells"][0]["article_ids"] == [art_id]
    assert "printer_options" in body

    summary = client.get(f"/events/{event_id}/configuration?fields=summary", headers=headers)
    assert summary.status_code == 200, summary.text
    sbody = summary.json()
    assert sbody["stations"][0]["article_ids"] == [art_id]
    assert sbody["app_layouts"][0]["cells"] == []


def test_configuration_api_put_returns_read_model():
    event_id, art_id, layout_uuid, st_uuid, email = _api_seed()
    token = _token(email)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "stations": [
            {
                "uuid": st_uuid,
                "name": "Bar",
                "printer_appliance_id": None,
                "article_ids": [art_id],
                "printer_rules": [],
            }
        ],
        "event_waiters": [],
        "app_layouts": [
            {
                "uuid": layout_uuid,
                "name": "Standard",
                "is_default": True,
                "grid_width": 2,
                "grid_height": 2,
                "cells": [
                    {
                        "row": 0,
                        "col": 0,
                        "label": "Cola",
                        "color": "#317EE3",
                        "article_ids": [art_id],
                        "voucher_definition_uuids": [],
                    }
                ],
            }
        ],
        "cash_registers": [],
        "voucher_definitions": [],
        "kitchen_monitors": [],
    }
    resp = client.put(f"/events/{event_id}/configuration", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stations"][0]["article_ids"] == [art_id]
    assert body["app_layouts"][0]["cells"][0]["label"] == "Cola"
    assert "printer_options" in body


def test_station_article_tree_api():
    event_id, art_id, _layout_uuid, _st_uuid, email = _api_seed()
    token = _token(email)
    resp = client.get(
        f"/events/{event_id}/station-article-tree",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    nodes = resp.json()["nodes"]
    assert nodes
    leaves = [c for n in nodes for c in n.get("children", [])]
    assert any(c.get("data", {}).get("article_id") == art_id for c in leaves)
