"""Event bookkeeping HTTP route."""

from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import (
    AccountingAccount,
    AccountingAccountPaymentTypeDefault,
    AccountingAccountTaxCodeDefault,
    Article,
    ArticleCategory,
    Event,
    HireCompany,
    Organisation,
    PaymentType,
    TaxCode,
    TaxCodeRate,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from tests.helpers import ensure_country

client = TestClient(app)


def _bookkeeping_fixture() -> tuple[str, int]:
    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        ch = ensure_country(db, "CH")
        hc = HireCompany(name=f"Bookkeeping HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Bookkeeping Org {suffix}",
            country_id=ch,
            hire_company_id=hc.id,
            currency="CHF",
            accounts_enabled=True,
            vat_liable=True,
        )
        db.add(org)
        db.flush()
        now = datetime.now(timezone.utc)
        ev = Event(
            name="Fest",
            status="prod",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_mode="pay_now",
            payment_types=["cash"],
        )
        db.add(ev)
        db.flush()
        tax = TaxCode(country_id=ch, name=f"Normalsatz {suffix}")
        db.add(tax)
        db.flush()
        db.add(TaxCodeRate(tax_code_id=tax.id, rate_percent=8.1, valid_from=date(2024, 1, 1)))
        revenue = AccountingAccount(organisation_id=org.id, name="Ertrag", number="3400")
        cash = AccountingAccount(organisation_id=org.id, name="Kasse", number="1000")
        vat_acc = AccountingAccount(organisation_id=org.id, name="MWST", number="2200")
        db.add_all([revenue, cash, vat_acc])
        db.flush()
        cat = ArticleCategory(name="Food", organisation_id=org.id, accounting_account_id=revenue.id)
        db.add(cat)
        db.flush()
        db.add(
            Article(
                name="Bier",
                label="Bier",
                price=5.0,
                article_category_id=cat.id,
                tax_code_id=tax.id,
                accounting_account_id=revenue.id,
            )
        )
        pt = db.query(PaymentType).filter(PaymentType.slug == "cash").first()
        if pt is None:
            pt = PaymentType(slug="cash", sort_order=0, is_active=True)
            db.add(pt)
            db.flush()
        db.add(
            AccountingAccountPaymentTypeDefault(
                organisation_id=org.id,
                payment_type_id=pt.id,
                accounting_account_id=cash.id,
            )
        )
        db.add(
            AccountingAccountTaxCodeDefault(
                organisation_id=org.id,
                tax_code_id=tax.id,
                accounting_account_id=vat_acc.id,
            )
        )
        db.add(
            User(
                email=f"bookkeeping-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return f"bookkeeping-{suffix}@test.local", ev.id
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_event_bookkeeping_route_returns_report():
    email, event_id = _bookkeeping_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/bookkeeping?view=summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "summary" in body or "detail" in body or "lines" in body
