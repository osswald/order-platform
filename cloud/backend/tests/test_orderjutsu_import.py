"""Tests for Orderjutsu event import parser, preview, and commit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.database import Base
from app.main import app
from app.models import (
    Article,
    ArticleCategory,
    ArticleIngredientLink,
    Event,
    HireCompany,
    Ingredient,
    Organisation,
    User,
    Waiter,
)
from app.orderjutsu_import import (
    OjImportError,
    OjProduct,
    build_preview,
    collect_ingredient_bom,
    collect_products,
    collect_sellable_refs,
    commit_orderjutsu_import,
    parse_orderjutsu_payload,
    suggest_article_matches,
    suggest_ingredient_matches,
    suggest_waiter_matches,
)
from app.roles import ROLE_MEMBER, ROLE_ORGANISATION_ADMIN, ROLE_PLATFORM_ADMIN, ROLE_TENANT_ADMIN
from app.schemas.orderjutsu_import import (
    OrderjutsuImportCommit,
    OrderjutsuImportCommitArticle,
    OrderjutsuImportCommitCashier,
    OrderjutsuImportCommitEvent,
    OrderjutsuImportCommitIngredient,
    OrderjutsuImportCommitStation,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country

FIXTURES = Path(__file__).parent / "fixtures" / "orderjutsu"
client = TestClient(app)


def _load_fixture(name: str) -> dict:
    with open(FIXTURES / name, encoding="utf-8") as fp:
        return json.load(fp)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    ch_country_id = ensure_country(session, "CH", country_id=1)
    session.add_all(
        [
            HireCompany(id=1, name="HC"),
            Organisation(
                id=1,
                name="Org",
                country_id=ch_country_id,
                hire_company_id=1,
                currency="CHF",
                ingredients_enabled=False,
            ),
            ArticleCategory(id=1, name="Food", organisation_id=1),
            ArticleCategory(id=2, name="Getränk", organisation_id=1),
            Article(
                id=10,
                name="Hörnlibräu",
                label="Hörnlibräu",
                price=5.5,
                article_category_id=2,
                is_addition=False,
                import_article_number="oj:207",
            ),
            Waiter(id=1, name="Adrian", pin="0000", organisation_id=1),
            Ingredient(id=1, name="Burger Pattie", organisation_id=1),
        ]
    )
    session.commit()
    yield session
    session.close()


def test_parse_orderjutsu_payload_required_keys():
    with pytest.raises(OjImportError):
        parse_orderjutsu_payload({})
    parsed = parse_orderjutsu_payload(_load_fixture("raclette_minimal.json"))
    assert parsed.label == "Vorlage Raclette-Plausch 2024"
    assert parsed.currency == "CHF"
    assert parsed.start.tzinfo is not None


def test_collect_products_dedupes_by_ref():
    parsed = parse_orderjutsu_payload(_load_fixture("raclette_minimal.json"))
    products = collect_products(parsed)
    refs = {p.ref for p in products}
    assert len(refs) == len(products)
    assert all(p.bon_text for p in products)


def test_collect_ingredient_bom_esaf():
    parsed = parse_orderjutsu_payload(_load_fixture("esaf_minimal.json"))
    bom = collect_ingredient_bom(parsed)
    assert bom.rows
    assert bom.ingredient_refs
    assert bom.product_refs


def test_collect_sellable_refs_excludes_ingredient_only():
    parsed = parse_orderjutsu_payload(_load_fixture("esaf_minimal.json"))
    bom = collect_ingredient_bom(parsed)
    sellable = collect_sellable_refs(parsed, bom)
    ingredient_only = bom.ingredient_refs - sellable
    assert ingredient_only


def test_suggest_article_matches_by_import_number(db):
    parsed = parse_orderjutsu_payload(_load_fixture("raclette_minimal.json"))
    products = collect_products(parsed)
    bom = collect_ingredient_bom(parsed)
    sellable = collect_sellable_refs(parsed, bom)
    matches = suggest_article_matches(
        db, 1, products, sellable_refs=sellable, composite_refs=bom.product_refs
    )
    by_ref = {m["ref"]: m for m in matches}
    if 207 in by_ref:
        assert by_ref[207]["matched_article_id"] == 10
        assert by_ref[207]["match_kind"] == "import_number"


def test_suggest_article_matches_by_label_when_name_differs(db):
    db.add(
        Article(
            id=20,
            name="Bier - Quöllfrisch",
            label="Quöllfrisch 5 dl Hell",
            price=5.5,
            article_category_id=2,
            is_addition=False,
        )
    )
    db.commit()
    product = OjProduct(
        ref=999,
        label="Bier - Quöllfrisch",
        bon_text="Quöllfrisch 5 dl Hell",
        price=5.5,
        is_addition=False,
        monitor_stock=False,
        stock=0,
        is_voucher=False,
    )
    matches = suggest_article_matches(
        db,
        1,
        [product],
        sellable_refs={999},
        composite_refs=set(),
    )
    assert matches[0]["match_kind"] == "exact"
    assert matches[0]["matched_article_id"] == 20


def test_suggest_article_matches_ambiguous_when_label_shared(db):
    db.add_all(
        [
            Article(
                id=21,
                name="Mineral gross mit",
                label="Mineral mit",
                price=6.5,
                article_category_id=2,
                is_addition=False,
            ),
            Article(
                id=22,
                name="Mineral klein mit",
                label="Mineral mit",
                price=6.5,
                article_category_id=2,
                is_addition=False,
            ),
        ]
    )
    db.commit()
    product = OjProduct(
        ref=1000,
        label="Mineral gross",
        bon_text="Mineral mit",
        price=6.5,
        is_addition=False,
        monitor_stock=False,
        stock=0,
        is_voucher=False,
    )
    matches = suggest_article_matches(
        db,
        1,
        [product],
        sellable_refs={1000},
        composite_refs=set(),
    )
    assert matches[0]["match_kind"] == "ambiguous"
    assert set(matches[0]["ambiguous_article_ids"]) == {21, 22}


def test_suggest_article_matches_ignores_price_difference(db):
    db.add(
        Article(
            id=30,
            name="Kaffee",
            label="Kaffee",
            price=3.0,
            article_category_id=2,
            is_addition=False,
        )
    )
    db.commit()
    product = OjProduct(
        ref=1001,
        label="Kaffee",
        bon_text="Kaffee",
        price=3.5,
        is_addition=False,
        monitor_stock=False,
        stock=0,
        is_voucher=False,
    )
    matches = suggest_article_matches(
        db,
        1,
        [product],
        sellable_refs={1001},
        composite_refs=set(),
    )
    assert matches[0]["match_kind"] == "exact"
    assert matches[0]["matched_article_id"] == 30
    assert matches[0]["matched_article_price"] == 3.0


def test_suggest_article_matches_ambiguous_same_text_different_prices(db):
    db.add_all(
        [
            Article(
                id=31,
                name="Kaffee klein",
                label="Kaffee",
                price=3.0,
                article_category_id=2,
                is_addition=False,
            ),
            Article(
                id=32,
                name="Kaffee gross",
                label="Kaffee",
                price=3.5,
                article_category_id=2,
                is_addition=False,
            ),
        ]
    )
    db.commit()
    product = OjProduct(
        ref=1002,
        label="Kaffee",
        bon_text="Kaffee",
        price=4.0,
        is_addition=False,
        monitor_stock=False,
        stock=0,
        is_voucher=False,
    )
    matches = suggest_article_matches(
        db,
        1,
        [product],
        sellable_refs={1002},
        composite_refs=set(),
    )
    assert matches[0]["match_kind"] == "ambiguous"
    assert set(matches[0]["ambiguous_article_ids"]) == {31, 32}


def test_suggest_ingredient_matches_by_name(db):
    parsed = parse_orderjutsu_payload(_load_fixture("esaf_minimal.json"))
    bom = collect_ingredient_bom(parsed)
    products = {p.ref: p for p in collect_products(parsed)}
    matches = suggest_ingredient_matches(db, 1, bom.ingredient_refs, products)
    if any(m["bon_text"] == "Burger Pattie" for m in matches):
        pattie = next(m for m in matches if m["bon_text"] == "Burger Pattie")
        assert pattie["matched_ingredient_id"] == 1


def test_suggest_waiter_matches_by_name(db):
    parsed = parse_orderjutsu_payload(_load_fixture("raclette_minimal.json"))
    matches = suggest_waiter_matches(db, 1, parsed.cashiers)
    by_name = {m["label"]: m for m in matches}
    assert by_name["Adrian"]["matched_waiter_id"] == 1


def test_build_preview_raclette(db):
    payload = _load_fixture("raclette_minimal.json")
    preview = build_preview(db, organisation_id=1, payload=payload)
    assert preview.event.name
    assert preview.products
    assert preview.cashiers
    assert preview.has_ingredients is False


def test_build_preview_esaf_has_ingredients(db):
    payload = _load_fixture("esaf_minimal.json")
    preview = build_preview(db, organisation_id=1, payload=payload)
    assert preview.has_ingredients is True
    assert preview.ingredients_enabled is False
    assert preview.ingredient_matches


def test_commit_raclette_minimal(db):
    payload = _load_fixture("raclette_minimal.json")
    preview = build_preview(db, organisation_id=1, payload=payload)
    commit = OrderjutsuImportCommit(
        organisation_id=1,
        payload=payload,
        event=OrderjutsuImportCommitEvent(
            name=preview.event.name + " Import",
            start=preview.event.start,
            end=preview.event.end,
        ),
        articles=[
            OrderjutsuImportCommitArticle(
                ref=p.ref,
                action="create_new" if p.match_kind == "none" else "link_existing",
                article_id=p.matched_article_id,
            )
            for p in preview.products
            if not p.ingredient_only
        ],
        cashiers=[
            OrderjutsuImportCommitCashier(
                index=c.index,
                action="event_only" if not c.matched_waiter_id else "link_existing",
                waiter_id=c.matched_waiter_id,
            )
            for c in preview.cashiers
        ],
        default_article_category_id=1,
        stations=[OrderjutsuImportCommitStation(index=st.index) for st in preview.stations],
        import_stock=True,
        import_vouchers=False,
    )
    result = commit_orderjutsu_import(db, commit, payload=payload)
    db.commit()
    event = db.query(Event).filter(Event.id == result.id).first()
    assert event is not None
    assert event.status == "config"
    assert event.stations
    assert event.app_layouts


def test_commit_succeeds_when_layout_contains_addition_ref(db):
    payload = {
        "label": "Glas layout test",
        "from": "2025-06-01 00:00:00",
        "to": "2025-08-02 08:17:27",
        "currency": "CHF",
        "app_layout": {
            "size": {"rows": 1, "cols": 1},
            "layout": [
                [
                    {
                        "title": "Bier",
                        "color": "#db3939",
                        "items": [{"ref": 100}, {"ref": 199}],
                        "textcolor": "white",
                    }
                ]
            ],
            "vouchers": [],
        },
        "cashiers": [
            {
                "label": "K1",
                "key": "0000",
                "is_extra": 0,
                "app_layout": {"size": {"rows": 0, "cols": 0}, "layout": [], "vouchers": []},
                "auto_table": 0,
            }
        ],
        "stations": [
            {
                "label": "Bar",
                "key": "0000",
                "products": [
                    {
                        "label": "Bier",
                        "bon_text": "Bier",
                        "price": 5.5,
                        "stock": 0,
                        "tax_percent": 0,
                        "monitor_stock": 0,
                        "extra": 0,
                        "is_voucher": 0,
                        "ref": 100,
                    },
                    {
                        "label": "Glas",
                        "bon_text": "Glas",
                        "price": 0,
                        "stock": 0,
                        "tax_percent": 0,
                        "monitor_stock": 0,
                        "extra": 1,
                        "is_voucher": 0,
                        "ref": 199,
                    },
                ],
            }
        ],
        "ingredients": [],
        "product_extras": [{"product_id": 100, "extra_id": 199}],
    }
    preview = build_preview(db, organisation_id=1, payload=payload)
    commit = OrderjutsuImportCommit(
        organisation_id=1,
        payload=payload,
        event=OrderjutsuImportCommitEvent(
            name="Glas layout import",
            start=preview.event.start,
            end=preview.event.end,
        ),
        articles=[
            OrderjutsuImportCommitArticle(ref=p.ref, action="create_new", article_id=None)
            for p in preview.products
            if not p.ingredient_only
        ],
        cashiers=[OrderjutsuImportCommitCashier(index=c.index, action="event_only") for c in preview.cashiers],
        default_article_category_id=1,
        stations=[OrderjutsuImportCommitStation(index=st.index) for st in preview.stations],
        import_stock=False,
        import_vouchers=False,
    )
    result = commit_orderjutsu_import(db, commit, payload=payload)
    db.commit()
    event = db.query(Event).filter(Event.id == result.id).first()
    assert event is not None
    layout = event.app_layouts[0]
    cell_article_ids = [art.id for cell in layout.cells for art in cell.articles]
    assert cell_article_ids
    assert all(not art.is_addition for art in db.query(Article).filter(Article.id.in_(cell_article_ids)).all())


def test_commit_esaf_enables_ingredients_and_recipes(db):
    payload = _load_fixture("esaf_minimal.json")
    preview = build_preview(db, organisation_id=1, payload=payload)
    commit = OrderjutsuImportCommit(
        organisation_id=1,
        payload=payload,
        enable_ingredients=True,
        event=OrderjutsuImportCommitEvent(
            name="ESAF Import",
            start=preview.event.start,
            end=preview.event.end,
        ),
        articles=[
            OrderjutsuImportCommitArticle(
                ref=p.ref,
                action="create_new",
                article_id=None,
            )
            for p in preview.products
            if not p.ingredient_only
        ],
        ingredients=[
            OrderjutsuImportCommitIngredient(ref=m.ref, action="create_new")
            for m in preview.ingredient_matches
        ],
        cashiers=[
            OrderjutsuImportCommitCashier(index=i, action="event_only")
            for i in range(len(preview.cashiers))
        ],
        default_article_category_id=1,
        stations=[OrderjutsuImportCommitStation(index=i) for i in range(len(preview.stations))],
        import_stock=True,
        import_vouchers=bool(preview.vouchers),
    )
    result = commit_orderjutsu_import(db, commit, payload=payload)
    db.commit()
    org = db.query(Organisation).filter(Organisation.id == 1).first()
    assert org.ingredients_enabled is True
    assert db.query(ArticleIngredientLink).count() > 0
    event = db.query(Event).filter(Event.id == result.id).first()
    assert event.vouchers_enabled or not preview.vouchers


def _setup_api_users():
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ch = ensure_country(db, "CH")
        hc = HireCompany(name="OJ HC")
        db.add(hc)
        db.flush()
        org = Organisation(name="OJ Org", country_id=ch, hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        tenant_admin = User(
            email="oj-tenant@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=hc.id,
        )
        org_admin = User(
            email="oj-org@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_ORGANISATION_ADMIN,
        )
        org_admin.organisations = [org]
        member = User(
            email="oj-member@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        member.organisations = [org]
        db.add_all([tenant_admin, org_admin, member])
        db.commit()
        return hc.id, org.id
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_preview_api_platform_admin():
    hc_id, org_id = _setup_api_users()
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        platform_admin = User(
            email="oj-platform@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
        )
        db.add(platform_admin)
        db.commit()
    finally:
        db.close()

    headers = {
        "Authorization": f"Bearer {_token('oj-platform@test.local')}",
        "X-Hire-Company-Id": str(hc_id),
    }
    payload = _load_fixture("raclette_minimal.json")
    r = client.post(
        "/events/import/orderjutsu/preview",
        headers=headers,
        json={"organisation_id": org_id, "payload": payload},
    )
    assert r.status_code == 200, r.text


def test_preview_api_org_admin():
    _, org_id = _setup_api_users()
    headers = {"Authorization": f"Bearer {_token('oj-org@test.local')}"}
    payload = _load_fixture("raclette_minimal.json")
    r = client.post(
        "/events/import/orderjutsu/preview",
        headers=headers,
        json={"organisation_id": org_id, "payload": payload},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["event"]["name"] == payload["label"]
    assert data["products"]


def test_preview_api_member_forbidden():
    _, org_id = _setup_api_users()
    headers = {"Authorization": f"Bearer {_token('oj-member@test.local')}"}
    payload = _load_fixture("raclette_minimal.json")
    r = client.post(
        "/events/import/orderjutsu/preview",
        headers=headers,
        json={"organisation_id": org_id, "payload": payload},
    )
    assert r.status_code == 403


def test_commit_api_org_admin_returns_configuration():
    _, org_id = _setup_api_users()
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        cat = ArticleCategory(name="Food", organisation_id=org_id)
        db.add(cat)
        db.flush()
        db.add(Waiter(name="Adrian", pin="0000", organisation_id=org_id))
        db.add(
            Article(
                name="Hörnlibräu",
                label="Hörnlibräu",
                price=5.5,
                article_category_id=cat.id,
                import_article_number="oj:207",
            )
        )
        db.commit()
        category_id = cat.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {_token('oj-org@test.local')}"}
    payload = _load_fixture("raclette_minimal.json")
    preview_resp = client.post(
        "/events/import/orderjutsu/preview",
        headers=headers,
        json={"organisation_id": org_id, "payload": payload},
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview = preview_resp.json()
    commit_body = {
        "organisation_id": org_id,
        "payload": payload,
        "event": {
            "name": preview["event"]["name"] + " API",
            "start": preview["event"]["start"],
            "end": preview["event"]["end"],
            "cash_registers_enabled": preview["has_cash_registers"],
            "vouchers_enabled": False,
        },
        "articles": [
            {
                "ref": p["ref"],
                "action": "create_new" if p["match_kind"] == "none" else "link_existing",
                "article_id": p.get("matched_article_id"),
            }
            for p in preview["products"]
            if not p.get("ingredient_only")
        ],
        "cashiers": [
            {
                "index": c["index"],
                "action": "event_only" if not c.get("matched_waiter_id") else "link_existing",
                "waiter_id": c.get("matched_waiter_id"),
            }
            for c in preview["cashiers"]
        ],
        "default_article_category_id": category_id,
        "stations": [{"index": st["index"], "printer_appliance_id": None} for st in preview["stations"]],
        "import_stock": True,
        "import_vouchers": False,
    }
    commit_resp = client.post(
        "/events/import/orderjutsu/commit",
        headers=headers,
        json=commit_body,
    )
    assert commit_resp.status_code == 200, commit_resp.text
    data = commit_resp.json()
    assert data["event_id"] > 0
    assert data["configuration"]["stations"]
