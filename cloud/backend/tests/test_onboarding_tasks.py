"""Onboarding checklist task detection for organisation dashboard."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.database import Base
from app.models import (
    AccountingAccount,
    AccountingAccountPaymentTypeDefault,
    AccountingAccountTaxCodeDefault,
    ApplianceLending,
    Article,
    ArticleAdditionLink,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventArticleStock,
    EventCashRegister,
    EventStation,
    EventWaiter,
    HireCompany,
    Organisation,
    PaymentType,
    TaxCode,
    TaxCodeRate,
    Waiter,
)
from app.onboarding_tasks import (
    build_onboarding_tasks,
    complete_onboarding_task,
    dismiss_onboarding_task,
    is_onboarding_dismissed,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_org(db, *, vat_liable=False, accounts_enabled=False, default_tax_code_id=None):
    ch_country_id = ensure_country(db, "CH", country_id=1)
    db.add(HireCompany(id=1, name="HC"))
    org = Organisation(
        id=1,
        hire_company_id=1,
        name="Test Org",
        country_id=ch_country_id,
        currency="CHF",
        vat_liable=vat_liable,
        accounts_enabled=accounts_enabled,
        default_tax_code_id=default_tax_code_id,
    )
    db.add(org)
    db.flush()
    return org


def _tax_code(db, country_id=1, name="Normal", rate=8.1):
    tax = TaxCode(id=1, country_id=country_id, name=name)
    db.add(tax)
    db.flush()
    db.add(TaxCodeRate(tax_code_id=tax.id, rate_percent=rate, valid_from=date(2024, 1, 1)))
    db.flush()
    return tax


def _event(db, org_id=1, **kwargs):
    now = datetime.now(UTC)
    defaults = dict(
        name="Fest",
        status="config",
        start=now + timedelta(days=3),
        end=now + timedelta(days=4),
        organisation_id=org_id,
        payment_mode="pay_later",
        payment_types=["cash"],
        cash_registers_enabled=False,
    )
    defaults.update(kwargs)
    event = Event(**defaults)
    db.add(event)
    db.flush()
    return event


def _task_map(result):
    return {task["id"]: task for task in result["tasks"]}


def test_empty_org_has_incomplete_catalogue_and_event_tasks(db):
    org = _seed_org(db)
    db.commit()
    result = build_onboarding_tasks(db, org, [], dismissed=False)
    tasks = _task_map(result)
    assert result["dismissed"] is False
    assert tasks["create_waiter"]["done"] is False
    assert tasks["create_article_group"]["done"] is False
    assert tasks["create_article"]["done"] is False
    assert tasks["create_event"]["done"] is False
    assert tasks["configure_vat"]["done"] is False
    assert tasks["configure_accounting"]["done"] is False


def test_configure_vat_done_when_liable_and_default_set(db):
    tax = _tax_code(db)
    org = _seed_org(db, vat_liable=True, default_tax_code_id=tax.id)
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["configure_vat"]["done"] is True


def test_accounting_subtasks_visible_only_when_enabled(db):
    org = _seed_org(db, accounts_enabled=False)
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["add_accounts"]["visible"] is False
    assert tasks["payment_type_defaults"]["visible"] is False

    org.accounts_enabled = True
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["add_accounts"]["visible"] is True
    assert tasks["add_accounts"]["done"] is False


def test_payment_type_defaults_complete(db):
    org = _seed_org(db, accounts_enabled=True)
    db.add(PaymentType(id=1, slug="cash", sort_order=0, is_active=True))
    account = AccountingAccount(id=1, organisation_id=1, name="Kasse", number="1000")
    db.add(account)
    db.flush()
    db.add(
        AccountingAccountPaymentTypeDefault(
            organisation_id=1,
            payment_type_id=1,
            accounting_account_id=1,
        )
    )
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["payment_type_defaults"]["done"] is True


def test_tax_code_defaults_only_when_vat_and_accounting(db):
    tax = _tax_code(db)
    org = _seed_org(db, vat_liable=True, accounts_enabled=True, default_tax_code_id=tax.id)
    db.add(AccountingAccount(id=1, organisation_id=1, name="MWST", number="2200"))
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["tax_code_defaults"]["visible"] is True
    assert tasks["tax_code_defaults"]["done"] is False

    db.add(
        AccountingAccountTaxCodeDefault(
            organisation_id=1,
            tax_code_id=tax.id,
            accounting_account_id=1,
        )
    )
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["tax_code_defaults"]["done"] is True


def test_catalogue_tasks_complete(db):
    org = _seed_org(db)
    db.add(Waiter(name="Anna", pin="1234", organisation_id=1))
    cat = ArticleCategory(id=1, name="Food", organisation_id=1)
    db.add(cat)
    db.flush()
    db.add(
        Article(
            id=1,
            name="Burger",
            label="Burger",
            price=10.0,
            article_category_id=1,
            is_addition=False,
        )
    )
    db.add(
        Article(
            id=2,
            name="Käse",
            label="Käse",
            price=1.0,
            article_category_id=1,
            is_addition=True,
        )
    )
    db.flush()
    db.add(ArticleAdditionLink(base_article_id=1, addition_article_id=2, sort_order=0))
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["create_waiter"]["done"] is True
    assert tasks["create_article_group"]["done"] is True
    assert tasks["create_article"]["done"] is True
    assert tasks["create_addon_linked"]["done"] is True


def test_event_tasks_any_event_satisfied(db):
    org = _seed_org(db)
    event = _event(db)
    db.add(EventWaiter(event_id=event.id, name="Bob", pin="1111"))
    station = EventStation(event_id=event.id, name="Bar")
    db.add(station)
    layout = EventAppLayout(event_id=event.id, name="Default", is_default=True, grid_width=4, grid_height=4)
    db.add(layout)
    db.flush()
    db.add(
        EventCashRegister(
            event_id=event.id,
            name="K1",
            pickup_code_prefix="A",
            pin="0000",
            layout_uuid=layout.uuid,
        )
    )
    db.commit()
    event.cash_registers_enabled = True
    db.commit()

    tasks = _task_map(build_onboarding_tasks(db, org, [event], dismissed=False))
    assert tasks["create_event"]["done"] is True
    assert tasks["enable_cash_registers"]["done"] is True
    assert tasks["add_cash_register"]["done"] is True
    assert tasks["add_event_waiter"]["done"] is True
    assert tasks["add_station"]["done"] is True
    assert tasks["create_app_layout"]["done"] is True
    assert tasks["add_article_to_station"]["done"] is False


def test_event_target_prefers_incomplete_event(db):
    org = _seed_org(db)
    older = _event(db, id=1, name="Old")
    newer = _event(db, id=2, name="New")
    db.add(EventWaiter(event_id=older.id, name="W", pin="1"))
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [older, newer], dismissed=False))
    assert tasks["add_event_waiter"]["done"] is True
    assert tasks["add_station"]["target_event_id"] == newer.id


def test_set_stock_task(db):
    org = _seed_org(db)
    event = _event(db)
    cat = ArticleCategory(id=1, name="Food", organisation_id=1)
    db.add(cat)
    db.flush()
    article = Article(
        id=1,
        name="Burger",
        label="Burger",
        price=10.0,
        article_category_id=1,
    )
    db.add(article)
    db.flush()
    station = EventStation(event_id=event.id, name="Bar")
    station.articles.append(article)
    db.add(station)
    db.flush()
    db.add(
        EventArticleStock(
            event_id=event.id,
            article_id=article.id,
            monitor_stock=True,
            in_stock=50,
        )
    )
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [event], dismissed=False))
    assert tasks["set_stock"]["done"] is True


def test_assign_article_tax_codes_when_vat_liable(db):
    tax = _tax_code(db)
    org = _seed_org(db, vat_liable=True, default_tax_code_id=tax.id)
    cat = ArticleCategory(id=1, name="Food", organisation_id=1)
    db.add(cat)
    db.flush()
    db.add(
        Article(
            id=1,
            name="Burger",
            label="Burger",
            price=10.0,
            article_category_id=1,
            tax_code_id=None,
        )
    )
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["assign_article_tax_codes"]["visible"] is True
    assert tasks["assign_article_tax_codes"]["done"] is False


def test_appliance_lending_task(db):
    org = _seed_org(db)
    from app.models import Appliance

    db.add(Appliance(id=1, hire_company_id=1, name="Pi", type="server"))
    today = date.today()
    db.add(
        ApplianceLending(
            appliance_id=1,
            organisation_id=1,
            start_date=today,
            end_date=today + timedelta(days=1),
        )
    )
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False))
    assert tasks["appliance_lending"]["done"] is True


def test_dismissed_returns_empty_tasks(db):
    org = _seed_org(db)
    db.commit()
    result = build_onboarding_tasks(db, org, [], dismissed=True)
    assert result["dismissed"] is True
    assert result["tasks"] == []


def test_manual_complete_marks_task_done_without_data(db):
    org = _seed_org(db)
    db.commit()
    complete_onboarding_task(db, user_id=1, organisation_id=org.id, task_id="create_waiter")
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False, user_id=1))
    assert tasks["create_waiter"]["done"] is True
    assert tasks["create_waiter"]["done_manually"] is True


def test_per_task_dismiss_hides_task(db):
    org = _seed_org(db)
    db.commit()
    dismiss_onboarding_task(db, user_id=1, organisation_id=org.id, task_id="create_waiter")
    db.commit()
    tasks = _task_map(build_onboarding_tasks(db, org, [], dismissed=False, user_id=1))
    assert "create_waiter" not in tasks
    assert "create_article_group" in tasks
