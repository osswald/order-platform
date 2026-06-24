"""Per-event bookkeeping journal summaries."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session, joinedload

from .accounting_validation import resolve_article_accounting_account_id
from .currency import event_currency
from .edge_reporting import _distinct_order_key
from .event_sales import _build_name_maps, _resolve_waiter_name, payment_type_label
from .fiscal_snapshot import effective_tax_rate_percent
from .fiscal_vat import split_gross_cents
from .models import (
    AccountingAccount,
    AccountingAccountPaymentTypeDefault,
    AccountingAccountTaxCodeDefault,
    Article,
    EdgeOrderItem,
    EdgePayment,
    Event,
    Organisation,
    PaymentType,
    TaxCode,
)


def _account_dict(account: AccountingAccount | None) -> dict[str, Any] | None:
    if account is None:
        return None
    return {"id": account.id, "number": account.number, "name": account.name}


def _load_event_bookkeeping_context(db: Session, *, organisation_id: int, event_id: int) -> Event | None:
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.event_waiters),
            joinedload(Event.cash_registers),
        )
        .filter(Event.id == event_id, Event.organisation_id == organisation_id)
        .first()
    )


def _payment_type_account_map(db: Session, organisation_id: int) -> dict[str, AccountingAccount]:
    rows = (
        db.query(PaymentType.slug, AccountingAccount)
        .join(
            AccountingAccountPaymentTypeDefault,
            AccountingAccountPaymentTypeDefault.payment_type_id == PaymentType.id,
        )
        .join(AccountingAccount, AccountingAccount.id == AccountingAccountPaymentTypeDefault.accounting_account_id)
        .filter(AccountingAccountPaymentTypeDefault.organisation_id == organisation_id)
        .all()
    )
    return {slug: account for slug, account in rows}


def _tax_code_account_map(db: Session, organisation_id: int) -> dict[int, AccountingAccount]:
    rows = (
        db.query(AccountingAccountTaxCodeDefault.tax_code_id, AccountingAccount)
        .join(AccountingAccount, AccountingAccount.id == AccountingAccountTaxCodeDefault.accounting_account_id)
        .filter(AccountingAccountTaxCodeDefault.organisation_id == organisation_id)
        .all()
    )
    return {tax_code_id: account for tax_code_id, account in rows}


def _tax_code_name_map(db: Session, country_id: int) -> dict[int, TaxCode]:
    rows = db.query(TaxCode).filter(TaxCode.country_id == country_id).all()
    return {row.id: row for row in rows}


def _subsidiary_for_item(event: Event, item: EdgeOrderItem, maps: dict) -> tuple[str | None, str | None]:
    if (item.order_source or "").lower() == "cash_register" and item.cash_register_uuid:
        for reg in event.cash_registers or []:
            if str(reg.uuid) == str(item.cash_register_uuid):
                return getattr(reg, "subsidiary_code", None), reg.name
    if item.waiter_uuid:
        name = _resolve_waiter_name(maps, item.waiter_uuid)
        for ew in event.event_waiters or []:
            if str(ew.uuid) == str(item.waiter_uuid):
                return getattr(ew, "subsidiary_code", None), name
        return None, name
    return None, None


def _resolve_line_fiscal(
    db: Session,
    organisation: Organisation,
    item: EdgeOrderItem,
    articles_by_id: dict[int, Article],
    tax_names: dict[int, TaxCode],
) -> tuple[int, int, int, int | None, float | None, int | None, bool]:
    gross = int(item.line_total_cents or 0)
    net = item.net_cents
    vat = item.vat_cents
    tax_code_id = item.tax_code_id
    tax_rate = item.tax_rate_percent
    accounting_account_id = item.accounting_account_id
    incomplete = False

    if net is None or vat is None or tax_code_id is None:
        incomplete = True
        article = articles_by_id.get(int(item.article_id)) if item.article_id is not None else None
        if article is not None:
            if tax_code_id is None and organisation.vat_liable:
                tax_code_id = article.tax_code_id
            if accounting_account_id is None and organisation.accounts_enabled:
                category = article.article_category
                accounting_account_id = resolve_article_accounting_account_id(
                    db,
                    organisation,
                    category,
                    article.accounting_account_id,
                )
        if tax_rate is None and tax_code_id is not None:
            tax_rate = effective_tax_rate_percent(db, tax_code_id)
        gross, net, vat = split_gross_cents(gross, tax_rate)

    return gross, int(net or 0), int(vat or 0), tax_code_id, tax_rate, accounting_account_id, incomplete


def _collective_bill_meta(item: EdgeOrderItem) -> tuple[str | None, str | None]:
    payload = item.payload if isinstance(item.payload, dict) else {}
    return payload.get("collective_bill_uuid"), payload.get("collective_bill_name")


def _journal_line_key(
    *,
    debit_account_id: int | None,
    credit_account_id: int | None,
    vat_account_id: int | None,
    tax_code_id: int | None,
    subsidiary_code: str | None,
    collective_bill_uuid: str | None,
    side: str,
) -> tuple:
    return (
        side,
        debit_account_id,
        credit_account_id,
        vat_account_id,
        tax_code_id,
        subsidiary_code or "",
        collective_bill_uuid or "",
    )


def build_event_bookkeeping_report(
    db: Session,
    *,
    organisation_id: int,
    event_id: int,
    view: str = "both",
) -> dict[str, Any]:
    event = _load_event_bookkeeping_context(db, organisation_id=organisation_id, event_id=event_id)
    if not event:
        return {"error": "event_not_found"}

    organisation = event.organisation
    if not organisation or not organisation.accounts_enabled:
        return {
            "event_id": event_id,
            "configuration_ok": False,
            "error": "accounts_not_enabled",
            "currency": event_currency(event, "CHF"),
            "summary": [],
            "detail": [],
            "warnings": ["Organisation accounting is not enabled."],
        }

    maps = _build_name_maps(db, event)
    payment_accounts = _payment_type_account_map(db, organisation_id)
    vat_accounts = _tax_code_account_map(db, organisation_id)
    tax_names = _tax_code_name_map(db, organisation.country_id)
    accounts_by_id = {
        row.id: row
        for row in db.query(AccountingAccount).filter(AccountingAccount.organisation_id == organisation_id).all()
    }

    paid_items = (
        db.query(EdgeOrderItem)
        .filter(
            EdgeOrderItem.organisation_id == organisation_id,
            EdgeOrderItem.event_id == event_id,
            EdgeOrderItem.payment_status == "paid",
        )
        .order_by(EdgeOrderItem.id.asc())
        .all()
    )
    seen_keys: set[str] = set()
    deduped_items: list[EdgeOrderItem] = []
    for item in paid_items:
        key = _distinct_order_key(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_items.append(item)

    article_ids = {int(i.article_id) for i in deduped_items if i.article_id is not None}
    articles_by_id = {}
    if article_ids:
        articles_by_id = {
            a.id: a
            for a in (
                db.query(Article)
                .options(joinedload(Article.article_category))
                .filter(Article.id.in_(article_ids))
                .all()
            )
        }

    warnings: list[str] = []
    missing_accounts: set[str] = set()
    snapshot_incomplete = False
    detail_entries: list[dict[str, Any]] = []
    summary_buckets: dict[tuple, dict[str, Any]] = defaultdict(
        lambda: {
            "net_cents": 0,
            "vat_cents": 0,
            "gross_cents": 0,
        }
    )

    payments = (
        db.query(EdgePayment)
        .filter(
            EdgePayment.organisation_id == organisation_id,
            EdgePayment.event_id == event_id,
        )
        .order_by(EdgePayment.id.asc())
        .all()
    )
    payments_by_submission: dict[int | None, list[EdgePayment]] = defaultdict(list)
    for payment in payments:
        payments_by_submission[payment.submission_id].append(payment)

    items_by_submission: dict[int | None, list[EdgeOrderItem]] = defaultdict(list)
    for item in deduped_items:
        items_by_submission[item.submission_id].append(item)

    def add_summary_line(
        *,
        debit_account: AccountingAccount | None,
        credit_account: AccountingAccount | None,
        vat_account: AccountingAccount | None,
        tax_code_id: int | None,
        tax_rate: float | None,
        subsidiary_code: str | None,
        subsidiary_name: str | None,
        collective_bill_uuid: str | None,
        collective_bill_name: str | None,
        net_cents: int,
        vat_cents: int,
        gross_cents: int,
        side: str,
    ) -> None:
        key = _journal_line_key(
            debit_account_id=debit_account.id if debit_account else None,
            credit_account_id=credit_account.id if credit_account else None,
            vat_account_id=vat_account.id if vat_account else None,
            tax_code_id=tax_code_id,
            subsidiary_code=subsidiary_code,
            collective_bill_uuid=collective_bill_uuid,
            side=side,
        )
        bucket = summary_buckets[key]
        if bucket.get("debit_account") is None:
            bucket.update(
                {
                    "debit_account": _account_dict(debit_account),
                    "credit_account": _account_dict(credit_account),
                    "vat_account": _account_dict(vat_account),
                    "tax_code": (
                        {
                            "id": tax_code_id,
                            "name": tax_names[tax_code_id].name if tax_code_id in tax_names else None,
                            "rate_percent": tax_rate,
                        }
                        if tax_code_id is not None
                        else None
                    ),
                    "subsidiary_code": subsidiary_code,
                    "subsidiary_name": subsidiary_name,
                    "collective_bill_uuid": collective_bill_uuid,
                    "collective_bill_name": collective_bill_name,
                    "side": side,
                }
            )
        bucket["net_cents"] += net_cents
        bucket["vat_cents"] += vat_cents
        bucket["gross_cents"] += gross_cents

    def process_line_item(item: EdgeOrderItem, debit_account: AccountingAccount | None) -> list[dict[str, Any]]:
        nonlocal snapshot_incomplete
        gross, net, vat, tax_code_id, tax_rate, accounting_account_id, incomplete = _resolve_line_fiscal(
            db, organisation, item, articles_by_id, tax_names
        )
        if incomplete:
            snapshot_incomplete = True

        credit_account = accounts_by_id.get(accounting_account_id) if accounting_account_id else None
        vat_account = vat_accounts.get(tax_code_id) if tax_code_id is not None else None
        subsidiary_code, subsidiary_name = _subsidiary_for_item(event, item, maps)
        bill_uuid, bill_name = _collective_bill_meta(item)

        if debit_account is None and (event.payment_mode or "") != "instant":
            missing_accounts.add("payment_type")
        if credit_account is None:
            missing_accounts.add("revenue")
        if vat > 0 and tax_code_id is not None and vat_account is None:
            missing_accounts.add(f"vat:{tax_code_id}")

        lines: list[dict[str, Any]] = []
        if gross > 0:
            haben_line = {
                "side": "credit",
                "account": _account_dict(credit_account),
                "amount_cents": net,
                "amount_kind": "net",
                "tax_code": (
                    {
                        "id": tax_code_id,
                        "name": tax_names[tax_code_id].name if tax_code_id in tax_names else None,
                        "rate_percent": tax_rate,
                    }
                    if tax_code_id is not None
                    else None
                ),
                "subsidiary_code": subsidiary_code,
                "subsidiary_name": subsidiary_name,
                "collective_bill_uuid": bill_uuid,
                "collective_bill_name": bill_name,
            }
            lines.append(haben_line)
            if vat > 0:
                lines.append(
                    {
                        "side": "credit",
                        "account": _account_dict(vat_account),
                        "amount_cents": vat,
                        "amount_kind": "vat",
                        "tax_code": haben_line["tax_code"],
                        "subsidiary_code": subsidiary_code,
                        "subsidiary_name": subsidiary_name,
                        "collective_bill_uuid": bill_uuid,
                        "collective_bill_name": bill_name,
                    }
                )
            if debit_account is not None:
                lines.insert(
                    0,
                    {
                        "side": "debit",
                        "account": _account_dict(debit_account),
                        "amount_cents": gross,
                        "amount_kind": "gross",
                        "subsidiary_code": subsidiary_code,
                        "subsidiary_name": subsidiary_name,
                        "collective_bill_uuid": bill_uuid,
                        "collective_bill_name": bill_name,
                    },
                )
                add_summary_line(
                    debit_account=debit_account,
                    credit_account=credit_account,
                    vat_account=vat_account,
                    tax_code_id=tax_code_id,
                    tax_rate=tax_rate,
                    subsidiary_code=subsidiary_code,
                    subsidiary_name=subsidiary_name,
                    collective_bill_uuid=bill_uuid,
                    collective_bill_name=bill_name,
                    net_cents=net,
                    vat_cents=vat,
                    gross_cents=gross,
                    side="payment",
                )
            else:
                add_summary_line(
                    debit_account=None,
                    credit_account=credit_account,
                    vat_account=vat_account,
                    tax_code_id=tax_code_id,
                    tax_rate=tax_rate,
                    subsidiary_code=subsidiary_code,
                    subsidiary_name=subsidiary_name,
                    collective_bill_uuid=bill_uuid,
                    collective_bill_name=bill_name,
                    net_cents=net,
                    vat_cents=vat,
                    gross_cents=gross,
                    side="instant",
                )
        return lines

    if payments:
        for payment in payments:
            submission_items = items_by_submission.get(payment.submission_id, [])
            if not submission_items:
                continue
            debit_account = payment_accounts.get((payment.method or "").lower())
            if debit_account is None:
                missing_accounts.add(f"payment:{payment.method}")
            total_gross = sum(int(i.line_total_cents or 0) for i in submission_items)
            allocated = 0
            journal_lines: list[dict[str, Any]] = []
            for idx, item in enumerate(submission_items):
                item_lines = process_line_item(item, debit_account)
                journal_lines.extend(item_lines)
                allocated += int(item.line_total_cents or 0)
            detail_entries.append(
                {
                    "kind": "payment",
                    "payment_id": payment.id,
                    "submission_id": payment.submission_id,
                    "method": payment.method,
                    "method_label": payment_type_label(payment.method),
                    "amount_cents": int(payment.amount_cents or 0),
                    "items_gross_cents": total_gross,
                    "paid_at": payment.created_at.isoformat() if payment.created_at else None,
                    "lines": journal_lines,
                }
            )
    else:
        for submission_id, submission_items in sorted(
            items_by_submission.items(), key=lambda x: (x[0] is None, x[0] or 0)
        ):
            journal_lines: list[dict[str, Any]] = []
            for item in submission_items:
                journal_lines.extend(process_line_item(item, None))
            if not journal_lines:
                continue
            bill_uuid, bill_name = _collective_bill_meta(submission_items[0])
            detail_entries.append(
                {
                    "kind": "order",
                    "submission_id": submission_id,
                    "collective_bill_uuid": bill_uuid,
                    "collective_bill_name": bill_name,
                    "lines": journal_lines,
                }
            )

    if snapshot_incomplete:
        warnings.append("Some line items use fallback article configuration (snapshot incomplete).")
    if missing_accounts:
        for key in sorted(missing_accounts):
            if key == "payment_type":
                warnings.append("Missing default account for one or more payment types.")
            elif key == "revenue":
                warnings.append("Missing revenue account on one or more articles.")
            elif key.startswith("vat:"):
                warnings.append("Missing VAT account for one or more tax codes.")
            elif key.startswith("payment:"):
                warnings.append(f"Missing account mapping for payment type {key.split(':', 1)[1]}.")

    configuration_ok = not any(
        w for w in warnings if "Missing" in w
    )

    summary = list(summary_buckets.values())
    result: dict[str, Any] = {
        "event_id": event_id,
        "currency": event_currency(event, "CHF"),
        "configuration_ok": configuration_ok,
        "warnings": warnings,
        "snapshot_incomplete": snapshot_incomplete,
        "summary": summary if view in ("summary", "both") else [],
        "detail": detail_entries if view in ("detail", "both") else [],
    }
    return result
