"""Tests for ingredient catalog and article ingredient links."""

from datetime import UTC, datetime

import pytest
from app.database import Base, SessionLocal
from app.ingredients import replace_ingredient_links, serialize_ingredient_links_for_admin
from app.main import app
from app.models import (
    Article,
    ArticleCategory,
    Event,
    EventStation,
    HireCompany,
    Ingredient,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
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
                ingredients_enabled=True,
            ),
            ArticleCategory(id=1, name="Food", organisation_id=1),
            Article(id=10, name="Pizza", label="P", price=12.0, article_category_id=1),
            Ingredient(id=1, name="Tomaten", organisation_id=1, unit="kg"),
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


def test_replace_ingredient_links(db):
    base = db.query(Article).filter(Article.id == 10).first()
    links = replace_ingredient_links(
        db,
        base,
        [{"ingredient_id": 1, "amount": 0.3, "sort_order": 0}],
    )
    db.commit()
    assert len(links) == 1
    items = serialize_ingredient_links_for_admin(db, base)
    assert items[0]["amount"] == 0.3
    assert items[0]["name"] == "Tomaten"


def _seed_ingredients_admin():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Ingredients Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Ingredients Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
            ingredients_enabled=True,
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="ingredients-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
        )
        cat = ArticleCategory(name="Food", organisation_id=org.id)
        db.add(cat)
        db.flush()
        db.add(Article(name="Pizza", label="P", price=12.0, article_category_id=cat.id, is_addition=False))
        db.commit()
        return org.id
    finally:
        db.close()


def _headers():
    token = client.post("/auth/token", data={"username": "ingredients-admin@test.local", "password": "secret"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_ingredients_api_crud():
    org_id = _seed_ingredients_admin()
    headers = _headers()
    listed = client.get(f"/ingredients/?organisation_id={org_id}", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []

    created = client.post(
        "/ingredients/",
        headers=headers,
        json={"name": "Käse", "unit": "kg", "organisation_id": org_id},
    )
    assert created.status_code == 200
    ing_id = created.json()["id"]

    updated = client.put(
        f"/ingredients/{ing_id}",
        headers=headers,
        json={"name": "Mozzarella"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Mozzarella"

    got = client.get(f"/ingredients/{ing_id}", headers=headers)
    assert got.status_code == 200

    deleted = client.delete(f"/ingredients/{ing_id}", headers=headers)
    assert deleted.status_code == 204


def test_article_ingredients_endpoint():
    org_id = _seed_ingredients_admin()
    headers = _headers()
    db = SessionLocal()
    try:
        article_id = db.query(Article).join(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
    finally:
        db.close()

    created = client.post(
        "/ingredients/",
        headers=headers,
        json={"name": "Teig API", "organisation_id": org_id},
    )
    assert created.status_code == 200
    ing_id = created.json()["id"]

    put = client.put(
        f"/articles/{article_id}/ingredients",
        headers=headers,
        json={"items": [{"ingredient_id": ing_id, "amount": 2}]},
    )
    assert put.status_code == 200
    assert len(put.json()["items"]) == 1

    read = client.get(f"/articles/{article_id}/ingredients", headers=headers)
    assert read.status_code == 200
    assert read.json()["items"][0]["amount"] == 2


def test_article_ingredients_on_zusatz():
    org_id = _seed_ingredients_admin()
    headers = _headers()
    db = SessionLocal()
    try:
        cat = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first()
        zusatz = Article(
            name="Extra Käse",
            label="Käse",
            price=1.0,
            article_category_id=cat.id,
            is_addition=True,
        )
        db.add(zusatz)
        db.commit()
        zusatz_id = zusatz.id
    finally:
        db.close()

    created = client.post(
        "/ingredients/",
        headers=headers,
        json={"name": "Mozzarella", "organisation_id": org_id},
    )
    assert created.status_code == 200
    ing_id = created.json()["id"]

    put = client.put(
        f"/articles/{zusatz_id}/ingredients",
        headers=headers,
        json={"items": [{"ingredient_id": ing_id, "amount": 0.2}]},
    )
    assert put.status_code == 200
    assert put.json()["items"][0]["amount"] == 0.2

    read = client.get(f"/articles/{zusatz_id}/ingredients", headers=headers)
    assert read.status_code == 200
    assert len(read.json()["items"]) == 1


def test_ingredient_ids_for_event_includes_linked_zusatz(db):
    from app.ingredients import ingredient_ids_for_event
    from app.models import ArticleAdditionLink

    db.add(
        Article(
            id=20,
            name="Käse",
            label="K",
            price=1.0,
            article_category_id=1,
            is_addition=True,
        )
    )
    db.add(ArticleAdditionLink(base_article_id=10, addition_article_id=20, sort_order=0))
    station = EventStation(event_id=1, name="Bar", sort_order=0)
    station.articles.append(db.query(Article).filter(Article.id == 10).first())
    db.add(station)
    db.flush()
    replace_ingredient_links(
        db,
        db.query(Article).filter(Article.id == 20).first(),
        [{"ingredient_id": 1, "amount": 0.5}],
    )
    db.commit()
    event = db.query(Event).filter(Event.id == 1).first()
    assert ingredient_ids_for_event(db, event) == {1}


def test_event_stock_excludes_composite_zusatz(db):
    from app.ingredients import event_stock_article_ids_with_additions
    from app.models import ArticleAdditionLink

    db.add(
        Article(
            id=20,
            name="Käse",
            label="K",
            price=1.0,
            article_category_id=1,
            is_addition=True,
        )
    )
    db.add(ArticleAdditionLink(base_article_id=10, addition_article_id=20, sort_order=0))
    station = EventStation(event_id=1, name="Bar", sort_order=0)
    station.articles.append(db.query(Article).filter(Article.id == 10).first())
    db.add(station)
    db.flush()
    replace_ingredient_links(
        db,
        db.query(Article).filter(Article.id == 20).first(),
        [{"ingredient_id": 1, "amount": 0.5}],
    )
    db.commit()
    event = db.query(Event).filter(Event.id == 1).first()
    assert 20 not in event_stock_article_ids_with_additions(db, event)
    assert 10 in event_stock_article_ids_with_additions(db, event)
