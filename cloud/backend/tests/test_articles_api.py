"""Articles API CRUD and addition links."""

from app.database import SessionLocal
from app.main import app
from app.models import ArticleCategory, HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed_org_admin():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Articles Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(name="Articles Org", country_id=country_id_by_code(db, "CH"), hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        db.add(
            User(
                email="articles-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
        )
        db.add(ArticleCategory(name="Drinks", organisation_id=org.id))
        db.commit()
        return org.id
    finally:
        db.close()


def _token() -> str:
    r = client.post("/auth/token", data={"username": "articles-admin@test.local", "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_articles_crud_and_addition_links():
    org_id = _seed_org_admin()
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        cat_id = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
    finally:
        db.close()

    created = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Cola",
            "label": "COLA",
            "price": 4.5,
            "article_category_id": cat_id,
            "is_addition": False,
        },
    )
    assert created.status_code == 200, created.text
    base_id = created.json()["id"]
    assert created.json()["organisation_currency"] == "CHF"

    zusatz = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Ice",
            "label": "ICE",
            "price": 0.5,
            "article_category_id": cat_id,
            "is_addition": True,
        },
    )
    assert zusatz.status_code == 200, zusatz.text
    add_id = zusatz.json()["id"]

    listed = client.get("/articles/", headers=headers)
    assert listed.status_code == 200
    cola_full = next(a for a in listed.json() if a["id"] == base_id)
    assert cola_full["organisation_currency"] == "CHF"

    updated = client.put(
        f"/articles/{base_id}",
        headers=headers,
        json={"price": 5.0},
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 5.0

    links = client.put(
        f"/articles/{base_id}/additions",
        headers=headers,
        json={"items": [{"addition_article_id": add_id, "sort_order": 0}]},
    )
    assert links.status_code == 200
    assert links.json()["items"][0]["addition_article_id"] == add_id

    read_links = client.get(f"/articles/{base_id}/additions", headers=headers)
    assert read_links.status_code == 200
    assert len(read_links.json()["items"]) == 1

    minimal = client.get(f"/articles/?organisation_id={org_id}&minimal=true", headers=headers)
    assert minimal.status_code == 200, minimal.text
    cola = next(a for a in minimal.json() if a["id"] == base_id)
    assert set(cola.keys()) == {"id", "name", "label", "organisation_id", "is_addition", "is_active"}
    assert cola["name"] == "Cola"
    assert cola["organisation_id"] == org_id


def test_article_is_active_defaults_true():
    org_id = _seed_org_admin()
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        cat_id = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
    finally:
        db.close()

    created = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Water",
            "label": "WATER",
            "price": 3.0,
            "article_category_id": cat_id,
            "is_addition": False,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["is_active"] is True


def test_article_is_active_update_and_active_only_filter():
    org_id = _seed_org_admin()
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        cat_id = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
    finally:
        db.close()

    active = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Active Beer",
            "label": "BEER",
            "price": 5.0,
            "article_category_id": cat_id,
            "is_addition": False,
        },
    )
    assert active.status_code == 200, active.text
    active_id = active.json()["id"]

    inactive = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Inactive Wine",
            "label": "WINE",
            "price": 6.0,
            "article_category_id": cat_id,
            "is_addition": False,
            "is_active": False,
        },
    )
    assert inactive.status_code == 200, inactive.text
    inactive_id = inactive.json()["id"]
    assert inactive.json()["is_active"] is False

    deactivated = client.put(
        f"/articles/{active_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    all_articles = client.get("/articles/", headers=headers)
    assert all_articles.status_code == 200
    assert {a["id"] for a in all_articles.json()} >= {active_id, inactive_id}

    active_only = client.get("/articles/?active_only=true", headers=headers)
    assert active_only.status_code == 200
    active_ids = {a["id"] for a in active_only.json()}
    assert active_id not in active_ids
    assert inactive_id not in active_ids


def test_addition_links_preserve_inactive_zusatz():
    org_id = _seed_org_admin()
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        cat_id = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
    finally:
        db.close()

    base = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Coffee",
            "label": "COFFEE",
            "price": 4.0,
            "article_category_id": cat_id,
            "is_addition": False,
        },
    )
    assert base.status_code == 200, base.text
    base_id = base.json()["id"]

    zusatz = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Milk",
            "label": "MILK",
            "price": 0.5,
            "article_category_id": cat_id,
            "is_addition": True,
        },
    )
    assert zusatz.status_code == 200, zusatz.text
    add_id = zusatz.json()["id"]

    linked = client.put(
        f"/articles/{base_id}/additions",
        headers=headers,
        json={"items": [{"addition_article_id": add_id, "sort_order": 0}]},
    )
    assert linked.status_code == 200

    deactivated = client.put(
        f"/articles/{add_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    relinked = client.put(
        f"/articles/{base_id}/additions",
        headers=headers,
        json={"items": [{"addition_article_id": add_id, "sort_order": 0}]},
    )
    assert relinked.status_code == 200
    assert relinked.json()["items"][0]["addition_article_id"] == add_id
