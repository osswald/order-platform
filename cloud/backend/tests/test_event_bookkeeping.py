"""Bookkeeping report builder."""

from datetime import date, datetime, timezone

import pytest

from app.event_bookkeeping import build_event_bookkeeping_report
from app.fiscal_vat import split_gross_cents
from app.models import (
    AccountingAccount,
    AccountingAccountPaymentTypeDefault,
    AccountingAccountTaxCodeDefault,
    Article,
    ArticleCategory,
    EdgeOrderItem,
    EdgePayment,
    Event,
    HireCompany,
    Organisation,
    PaymentType,
    TaxCode,
    TaxCodeRate,
)
from tests.helpers import ensure_country


@pytest.fixture
def bookkeeping_db(memory_db_session):
    ch = ensure_country(memory_db_session, "CH", country_id=1)
    hc = HireCompany(id=1, name="HC")
    memory_db_session.add(hc)
    org = Organisation(
        id=1,
        hire_company_id=1,
        name="Org",
        country_id=ch,
        currency="CHF",
        accounts_enabled=True,
        vat_liable=True,
    )
    memory_db_session.add(org)
    now = datetime.now(timezone.utc)
    ev = Event(
        id=1,
        name="Fest",
        status="prod",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_now",
        payment_types=["cash"],
    )
    memory_db_session.add(ev)
    tax = TaxCode(id=1, country_id=ch, name="Normalsatz")
    memory_db_session.add(tax)
    memory_db_session.add(TaxCodeRate(tax_code_id=1, rate_percent=8.1, valid_from=date(2024, 1, 1)))
    revenue = AccountingAccount(id=1, organisation_id=1, name="Ertrag Gastro", number="3400")
    cash = AccountingAccount(id=2, organisation_id=1, name="Kasse", number="1000")
    vat_acc = AccountingAccount(id=3, organisation_id=1, name="MWST 8.1%", number="2200")
    memory_db_session.add_all([revenue, cash, vat_acc])
    cat = ArticleCategory(id=1, name="Food", organisation_id=1, accounting_account_id=1)
    memory_db_session.add(cat)
    art = Article(
        id=10,
        name="Bier",
        label="Bier",
        price=5.0,
        article_category_id=1,
        tax_code_id=1,
        accounting_account_id=1,
    )
    memory_db_session.add(art)
    pt = PaymentType(id=1, slug="cash", sort_order=0, is_active=True)
    memory_db_session.add(pt)
    memory_db_session.add(
        AccountingAccountPaymentTypeDefault(
            organisation_id=1, payment_type_id=1, accounting_account_id=2
        )
    )
    memory_db_session.add(
        AccountingAccountTaxCodeDefault(organisation_id=1, tax_code_id=1, accounting_account_id=3)
    )
    gross, net, vat = split_gross_cents(500, 8.1)
    memory_db_session.add(
        EdgeOrderItem(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            session_id=1,
            submission_id=100,
            article_id=10,
            article_name="Bier",
            quantity=1,
            unit_price_cents=500,
            line_total_cents=gross,
            tax_code_id=1,
            tax_rate_percent=8.1,
            accounting_account_id=1,
            net_cents=net,
            vat_cents=vat,
            payment_status="paid",
            method="cash",
            payload={"gross_cents": gross, "net_cents": net, "vat_cents": vat},
        )
    )
    memory_db_session.add(
        EdgePayment(
            organisation_id=1,
            appliance_id=1,
            event_id=1,
            submission_id=100,
            method="cash",
            amount_cents=gross,
            payload={"type": "cash", "amount_cents": gross},
        )
    )
    memory_db_session.commit()
    return memory_db_session, ev


def test_split_gross_cents():
    gross, net, vat = split_gross_cents(1081, 8.1)
    assert gross == 1081
    assert net + vat == gross


def test_bookkeeping_payment_summary(bookkeeping_db):
    db, ev = bookkeeping_db
    report = build_event_bookkeeping_report(db, organisation_id=1, event_id=ev.id, view="both")
    assert report["configuration_ok"] is True
    assert len(report["summary"]) >= 1
    assert len(report["detail"]) == 1
    assert report["detail"][0]["method"] == "cash"
