"""Onboarding checklist task detection for the organisation dashboard."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session, joinedload

from .fiscal_snapshot import effective_tax_rate_percent
from .i18n.errors import api_error
from .models import (
    AccountingAccount,
    AccountingAccountPaymentTypeDefault,
    AccountingAccountTaxCodeDefault,
    ApplianceLending,
    Article,
    ArticleAdditionLink,
    ArticleCategory,
    Event,
    EventArticleStock,
    EventStation,
    Organisation,
    PaymentType,
    TaxCode,
    UserOrganisationOnboardingDismissal,
    UserOrganisationOnboardingTaskState,
    Waiter,
)

ONBOARDING_TASK_IDS = frozenset(
    {
        "configure_vat",
        "configure_accounting",
        "add_accounts",
        "payment_type_defaults",
        "tax_code_defaults",
        "default_category_account",
        "assign_article_tax_codes",
        "appliance_lending",
        "create_waiter",
        "create_article_group",
        "create_article",
        "create_addon_linked",
        "create_event",
        "enable_cash_registers",
        "add_cash_register",
        "add_event_waiter",
        "add_station",
        "add_article_to_station",
        "create_app_layout",
        "set_stock",
    }
)


def is_onboarding_dismissed(db: Session, *, user_id: int, organisation_id: int) -> bool:
    return (
        db.query(UserOrganisationOnboardingDismissal)
        .filter(
            UserOrganisationOnboardingDismissal.user_id == user_id,
            UserOrganisationOnboardingDismissal.organisation_id == organisation_id,
        )
        .first()
        is not None
    )


def _load_task_states(
    db: Session,
    *,
    user_id: int | None,
    organisation_id: int,
) -> dict[str, UserOrganisationOnboardingTaskState]:
    if user_id is None:
        return {}
    rows = (
        db.query(UserOrganisationOnboardingTaskState)
        .filter(
            UserOrganisationOnboardingTaskState.user_id == user_id,
            UserOrganisationOnboardingTaskState.organisation_id == organisation_id,
        )
        .all()
    )
    return {row.task_id: row for row in rows}


def ensure_valid_onboarding_task_id(task_id: str) -> None:
    if task_id not in ONBOARDING_TASK_IDS:
        raise api_error("onboarding_task_not_found", status.HTTP_404_NOT_FOUND)


def _get_or_create_task_state(
    db: Session,
    *,
    user_id: int,
    organisation_id: int,
    task_id: str,
) -> UserOrganisationOnboardingTaskState:
    ensure_valid_onboarding_task_id(task_id)
    row = (
        db.query(UserOrganisationOnboardingTaskState)
        .filter(
            UserOrganisationOnboardingTaskState.user_id == user_id,
            UserOrganisationOnboardingTaskState.organisation_id == organisation_id,
            UserOrganisationOnboardingTaskState.task_id == task_id,
        )
        .first()
    )
    if row is None:
        row = UserOrganisationOnboardingTaskState(
            user_id=user_id,
            organisation_id=organisation_id,
            task_id=task_id,
        )
        db.add(row)
    return row


def complete_onboarding_task(
    db: Session,
    *,
    user_id: int,
    organisation_id: int,
    task_id: str,
) -> None:
    row = _get_or_create_task_state(
        db,
        user_id=user_id,
        organisation_id=organisation_id,
        task_id=task_id,
    )
    row.manually_completed = True
    row.dismissed = False


def dismiss_onboarding_task(
    db: Session,
    *,
    user_id: int,
    organisation_id: int,
    task_id: str,
) -> None:
    row = _get_or_create_task_state(
        db,
        user_id=user_id,
        organisation_id=organisation_id,
        task_id=task_id,
    )
    row.dismissed = True


def _lending_bucket_counts(db: Session, organisation_id: int, today: date) -> dict[str, int]:
    rows = (
        db.query(ApplianceLending)
        .filter(ApplianceLending.organisation_id == organisation_id)
        .all()
    )
    current = planned = 0
    for row in rows:
        if row.returned_at is not None:
            continue
        if row.end_date < today:
            continue
        if row.start_date > today:
            planned += 1
            continue
        if row.start_date <= today <= row.end_date:
            current += 1
    return {"current": current, "planned": planned}


def _task(
    *,
    task_id: str,
    group: str,
    done: bool,
    visible: bool = True,
    done_manually: bool = False,
    target_route: str | None = None,
    target_params: dict[str, str] | None = None,
    target_query: dict[str, str] | None = None,
    target_event_id: int | None = None,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "group": group,
        "done": done,
        "done_manually": done_manually,
        "visible": visible,
        "target_route": target_route,
        "target_params": target_params,
        "target_query": target_query,
        "target_event_id": target_event_id,
    }


def _org_accounting_target(organisation_id: int) -> dict[str, Any]:
    return {
        "target_route": "organisations-detail",
        "target_params": {"id": str(organisation_id)},
        "target_query": {"section": "buchhaltung"},
    }


def _payment_type_defaults_complete(db: Session, organisation_id: int) -> bool:
    active_type_ids = [
        row.id
        for row in db.query(PaymentType.id).filter(PaymentType.is_active.is_(True)).all()
    ]
    if not active_type_ids:
        return True
    mapped = {
        row.payment_type_id
        for row in db.query(AccountingAccountPaymentTypeDefault.payment_type_id)
        .filter(AccountingAccountPaymentTypeDefault.organisation_id == organisation_id)
        .all()
    }
    return all(pt_id in mapped for pt_id in active_type_ids)


def _tax_code_defaults_complete(db: Session, organisation: Organisation) -> bool:
    tax_codes = (
        db.query(TaxCode.id)
        .filter(TaxCode.country_id == organisation.country_id)
        .all()
    )
    if not tax_codes:
        return True
    mapped = {
        row.tax_code_id
        for row in db.query(AccountingAccountTaxCodeDefault.tax_code_id)
        .filter(AccountingAccountTaxCodeDefault.organisation_id == organisation.id)
        .all()
    }
    for (tax_code_id,) in tax_codes:
        if effective_tax_rate_percent(db, tax_code_id) > 0 and tax_code_id not in mapped:
            return False
    return True


def _has_addon_link(db: Session, organisation_id: int) -> bool:
    return (
        db.query(ArticleAdditionLink.base_article_id)
        .join(Article, Article.id == ArticleAdditionLink.base_article_id)
        .join(ArticleCategory, ArticleCategory.id == Article.article_category_id)
        .filter(ArticleCategory.organisation_id == organisation_id)
        .first()
        is not None
    )


def _base_articles_missing_tax_codes(db: Session, organisation_id: int) -> bool:
    rows = (
        db.query(Article.id)
        .join(ArticleCategory, ArticleCategory.id == Article.article_category_id)
        .filter(
            ArticleCategory.organisation_id == organisation_id,
            Article.is_addition.is_(False),
            Article.tax_code_id.is_(None),
        )
        .first()
    )
    return rows is not None


def _has_default_category_account(db: Session, organisation_id: int) -> bool:
    return (
        db.query(AccountingAccount.id)
        .filter(
            AccountingAccount.organisation_id == organisation_id,
            AccountingAccount.is_default_for_article_categories.is_(True),
        )
        .first()
        is not None
    )


def _load_events(db: Session, events: list[Event]) -> list[Event]:
    if not events:
        return []
    event_ids = [event.id for event in events]
    loaded = (
        db.query(Event)
        .options(
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts),
            joinedload(Event.cash_registers),
        )
        .filter(Event.id.in_(event_ids))
        .all()
    )
    by_id = {event.id: event for event in loaded}
    return [by_id[event_id] for event_id in sorted(event_ids, reverse=True) if event_id in by_id]


def _stock_by_event(db: Session, event_ids: list[int]) -> dict[int, list[EventArticleStock]]:
    if not event_ids:
        return {}
    rows = db.query(EventArticleStock).filter(EventArticleStock.event_id.in_(event_ids)).all()
    out: dict[int, list[EventArticleStock]] = {}
    for row in rows:
        out.setdefault(row.event_id, []).append(row)
    return out


def _pick_target_event(
    events: list[Event],
    stock_by_event: dict[int, list[EventArticleStock]],
    *,
    predicate,
) -> int | None:
    if not events:
        return None
    for event in events:
        if not predicate(event, stock_by_event.get(event.id, [])):
            return event.id
    return events[0].id


def _event_predicates(stock_by_event: dict[int, list[EventArticleStock]]):
    return {
        "enable_cash_registers": lambda event, _stock: event.cash_registers_enabled,
        "add_cash_register": lambda event, _stock: len(event.cash_registers or []) > 0,
        "add_event_waiter": lambda event, _stock: len(event.event_waiters or []) > 0,
        "add_station": lambda event, _stock: len(event.stations or []) > 0,
        "add_article_to_station": lambda event, _stock: any(
            len(station.articles or []) > 0 for station in (event.stations or [])
        ),
        "create_app_layout": lambda event, _stock: len(event.app_layouts or []) > 0,
        "set_stock": lambda event, stock: any(
            row.monitor_stock and row.in_stock is not None for row in stock
        ),
    }


def build_onboarding_tasks(
    db: Session,
    organisation: Organisation,
    events: list[Event],
    *,
    dismissed: bool,
    user_id: int | None = None,
) -> dict[str, Any]:
    if dismissed:
        return {"dismissed": True, "tasks": []}

    task_states = _load_task_states(db, user_id=user_id, organisation_id=organisation.id)

    def finalize_task(task: dict[str, Any]) -> dict[str, Any] | None:
        state = task_states.get(task["id"])
        if state is not None and state.dismissed:
            return None
        auto_done = bool(task["done"])
        manually_completed = bool(state and state.manually_completed)
        task["done"] = auto_done or manually_completed
        task["done_manually"] = manually_completed
        return task

    organisation_id = organisation.id
    loaded_events = _load_events(db, events)
    event_ids = [event.id for event in loaded_events]
    stock_by_event = _stock_by_event(db, event_ids)
    predicates = _event_predicates(stock_by_event)

    waiters_count = db.query(Waiter).filter(Waiter.organisation_id == organisation_id).count()
    categories_count = (
        db.query(ArticleCategory).filter(ArticleCategory.organisation_id == organisation_id).count()
    )
    base_articles_count = (
        db.query(Article)
        .join(ArticleCategory, ArticleCategory.id == Article.article_category_id)
        .filter(
            ArticleCategory.organisation_id == organisation_id,
            Article.is_addition.is_(False),
        )
        .count()
    )
    accounts_count = (
        db.query(AccountingAccount)
        .filter(AccountingAccount.organisation_id == organisation_id)
        .count()
    )
    lending_counts = _lending_bucket_counts(db, organisation_id, datetime.now(UTC).date())
    has_lending = lending_counts["current"] > 0 or lending_counts["planned"] > 0

    org_target = _org_accounting_target(organisation_id)
    accounts_enabled = bool(organisation.accounts_enabled)
    vat_liable = bool(organisation.vat_liable)

    def event_target(section: str, task_id: str) -> dict[str, Any]:
        event_id = _pick_target_event(
            loaded_events,
            stock_by_event,
            predicate=predicates[task_id],
        )
        if event_id is None:
            return {
                "target_route": "events-new",
                "target_params": None,
                "target_query": None,
                "target_event_id": None,
            }
        return {
            "target_route": "events-detail",
            "target_params": {"id": str(event_id)},
            "target_query": {"section": section},
            "target_event_id": event_id,
        }

    tasks: list[dict[str, Any]] = [
        _task(
            task_id="configure_vat",
            group="organisation",
            done=vat_liable and organisation.default_tax_code_id is not None,
            **org_target,
        ),
        _task(
            task_id="configure_accounting",
            group="organisation",
            done=accounts_enabled,
            **org_target,
        ),
        _task(
            task_id="add_accounts",
            group="organisation",
            done=accounts_count >= 1,
            visible=accounts_enabled,
            **org_target,
        ),
        _task(
            task_id="payment_type_defaults",
            group="organisation",
            done=_payment_type_defaults_complete(db, organisation_id),
            visible=accounts_enabled,
            **org_target,
        ),
        _task(
            task_id="tax_code_defaults",
            group="organisation",
            done=_tax_code_defaults_complete(db, organisation),
            visible=vat_liable and accounts_enabled,
            **org_target,
        ),
        _task(
            task_id="default_category_account",
            group="organisation",
            done=_has_default_category_account(db, organisation_id),
            visible=accounts_enabled,
            **org_target,
        ),
        _task(
            task_id="assign_article_tax_codes",
            group="organisation",
            done=not _base_articles_missing_tax_codes(db, organisation_id),
            visible=vat_liable and base_articles_count > 0,
            **org_target,
        ),
        _task(
            task_id="appliance_lending",
            group="organisation",
            done=has_lending,
            target_route="appliance-lendings",
            target_params=None,
            target_query=None,
        ),
        _task(
            task_id="create_waiter",
            group="catalogue",
            done=waiters_count >= 1,
            target_route="waiters-new",
        ),
        _task(
            task_id="create_article_group",
            group="catalogue",
            done=categories_count >= 1,
            target_route="article-categories-new",
        ),
        _task(
            task_id="create_article",
            group="catalogue",
            done=base_articles_count >= 1,
            target_route="articles-new",
        ),
        _task(
            task_id="create_addon_linked",
            group="catalogue",
            done=_has_addon_link(db, organisation_id),
            target_route="articles-new",
            target_query={"type": "addition"},
        ),
        _task(
            task_id="create_event",
            group="event",
            done=len(loaded_events) > 0,
            target_route="events-new",
        ),
        _task(
            task_id="enable_cash_registers",
            group="event",
            done=any(predicates["enable_cash_registers"](event, []) for event in loaded_events),
            **event_target("stammdaten", "enable_cash_registers"),
        ),
        _task(
            task_id="add_cash_register",
            group="event",
            done=any(predicates["add_cash_register"](event, []) for event in loaded_events),
            **event_target("kassen", "add_cash_register"),
        ),
        _task(
            task_id="add_event_waiter",
            group="event",
            done=any(predicates["add_event_waiter"](event, []) for event in loaded_events),
            **event_target("kellner", "add_event_waiter"),
        ),
        _task(
            task_id="add_station",
            group="event",
            done=any(predicates["add_station"](event, []) for event in loaded_events),
            **event_target("stationen", "add_station"),
        ),
        _task(
            task_id="add_article_to_station",
            group="event",
            done=any(
                predicates["add_article_to_station"](event, stock_by_event.get(event.id, []))
                for event in loaded_events
            ),
            **event_target("stationen", "add_article_to_station"),
        ),
        _task(
            task_id="create_app_layout",
            group="event",
            done=any(predicates["create_app_layout"](event, []) for event in loaded_events),
            **event_target("layouts", "create_app_layout"),
        ),
        _task(
            task_id="set_stock",
            group="event",
            done=any(
                predicates["set_stock"](event, stock_by_event.get(event.id, []))
                for event in loaded_events
            ),
            **event_target("lager", "set_stock"),
        ),
    ]

    finalized_tasks = [task for task in (finalize_task(task) for task in tasks) if task is not None]
    return {"dismissed": False, "tasks": finalized_tasks}
