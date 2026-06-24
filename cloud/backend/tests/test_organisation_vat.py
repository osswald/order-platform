"""Organisation VAT settings and article tax code assignment."""

from datetime import date

from fastapi.testclient import TestClient

from app.database import SessionLocal, _ensure_keine_tax_codes
from app.main import app
from app.models import ArticleCategory, Country, HireCompany, Organisation, TaxCode, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed_tenant():
    db = SessionLocal()
    try:
        hc = HireCompany(name="VAT Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="VAT Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="vat-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
        )
        db.add(ArticleCategory(name="Food", organisation_id=org.id))
        db.commit()
        return org.id
    finally:
        db.close()


def _token() -> str:
    r = client.post("/auth/token", data={"username": "vat-admin@test.local", "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _tax_code_id(db, country_code: str, name: str) -> int:
    country_id = country_id_by_code(db, country_code)
    tax_code = (
        db.query(TaxCode)
        .filter(TaxCode.country_id == country_id, TaxCode.name == name)
        .first()
    )
    assert tax_code is not None, f"tax code {name!r} for {country_code!r} missing"
    return tax_code.id


def test_organisation_vat_settings():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    db = SessionLocal()
    try:
        ch_normalsatz = _tax_code_id(db, "CH", "Normalsatz")
    finally:
        db.close()

    missing_default = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"vat_liable": True},
    )
    assert missing_default.status_code == 400

    enabled = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"vat_liable": True, "default_tax_code_id": ch_normalsatz},
    )
    assert enabled.status_code == 200, enabled.text
    body = enabled.json()
    assert body["vat_liable"] is True
    assert body["default_tax_code_id"] == ch_normalsatz
    assert body["default_tax_code"]["name"] == "Normalsatz"

    disabled = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"vat_liable": False},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["vat_liable"] is False
    assert disabled.json()["default_tax_code_id"] is None


def test_organisation_country_change_rejects_mismatched_default():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    db = SessionLocal()
    try:
        ch_normalsatz = _tax_code_id(db, "CH", "Normalsatz")
        de_id = country_id_by_code(db, "DE")
    finally:
        db.close()

    client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"vat_liable": True, "default_tax_code_id": ch_normalsatz},
    )

    mismatch = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"country_id": de_id},
    )
    assert mismatch.status_code == 400


def test_articles_require_tax_code_when_vat_liable():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    db = SessionLocal()
    try:
        cat_id = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
        ch_normalsatz = _tax_code_id(db, "CH", "Normalsatz")
    finally:
        db.close()

    client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"vat_liable": True, "default_tax_code_id": ch_normalsatz},
    )

    missing = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Bread",
            "label": "BREAD",
            "price": 3.0,
            "article_category_id": cat_id,
        },
    )
    assert missing.status_code == 400

    created = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Bread",
            "label": "BREAD",
            "price": 3.0,
            "article_category_id": cat_id,
            "tax_code_id": ch_normalsatz,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["tax_code_id"] == ch_normalsatz
    assert created.json()["tax_code_name"] == "Normalsatz"


def test_articles_reject_tax_code_when_vat_not_liable():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    db = SessionLocal()
    try:
        cat_id = db.query(ArticleCategory).filter(ArticleCategory.organisation_id == org_id).first().id
        ch_normalsatz = _tax_code_id(db, "CH", "Normalsatz")
    finally:
        db.close()

    rejected = client.post(
        "/articles/",
        headers=headers,
        json={
            "name": "Water",
            "label": "WATER",
            "price": 2.0,
            "article_category_id": cat_id,
            "tax_code_id": ch_normalsatz,
        },
    )
    assert rejected.status_code == 400


def test_events_organisations_includes_vat_fields():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    listed = client.get("/events/organisations", headers=headers)
    assert listed.status_code == 200
    org = next(item for item in listed.json() if item["id"] == org_id)
    assert org["country_id"] is not None
    assert org["vat_liable"] is False
    assert org["default_tax_code_id"] is None
    assert org["accounts_enabled"] is False

    enabled = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"accounts_enabled": True},
    )
    assert enabled.status_code == 200, enabled.text

    relisted = client.get("/events/organisations", headers=headers)
    assert relisted.status_code == 200
    org_enabled = next(item for item in relisted.json() if item["id"] == org_id)
    assert org_enabled["accounts_enabled"] is True


def test_ensure_keine_tax_codes_for_reference_countries_only():
    db = SessionLocal()
    try:
        lux = Country(code="LU", name="Luxemburg")
        db.add(lux)
        db.commit()
        _ensure_keine_tax_codes()
        ch_id = country_id_by_code(db, "CH")
        lux_id = lux.id
        ch_keine = (
            db.query(TaxCode)
            .filter(TaxCode.country_id == ch_id, TaxCode.name == "Keine")
            .first()
        )
        lux_keine = (
            db.query(TaxCode)
            .filter(TaxCode.country_id == lux_id, TaxCode.name == "Keine")
            .first()
        )
        assert ch_keine is not None
        assert lux_keine is None
    finally:
        db.close()


def test_delete_tax_code_blocked_when_in_use():
    org_id = _seed_tenant()
    tenant_headers = {"Authorization": f"Bearer {_token()}"}

    db = SessionLocal()
    try:
        ch_normalsatz = _tax_code_id(db, "CH", "Normalsatz")
        platform = User(
            email="vat-platform@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            is_superuser=True,
        )
        db.add(platform)
        db.commit()
    finally:
        db.close()

    client.put(
        f"/organisations/{org_id}",
        headers=tenant_headers,
        json={"vat_liable": True, "default_tax_code_id": ch_normalsatz},
    )

    platform_token = client.post(
        "/auth/token",
        data={"username": "vat-platform@test.local", "password": "secret"},
    ).json()["access_token"]
    platform_headers = {"Authorization": f"Bearer {platform_token}"}

    blocked = client.delete(f"/tax-codes/{ch_normalsatz}", headers=platform_headers)
    assert blocked.status_code == 400
