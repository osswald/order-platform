"""Orderjutsu JSON event import: parse, preview, and commit."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session, joinedload

from .additions import replace_addition_links
from .event_config_validation import replace_event_configuration
from .i18n.errors import api_error
from .ingredient_stock import upsert_ingredient_stock_rows
from .ingredients import replace_ingredient_links
from .instant_collective_bill import apply_instant_collective_bill_settings
from .models import Article, ArticleCategory, Event, Ingredient, Organisation, Waiter
from .receipt_printing_config import copy_receipt_printing_from_organisation
from .schemas.orderjutsu_import import (
    OrderjutsuImportCommit,
    OrderjutsuImportPreview,
    OrderjutsuImportPreviewCashier,
    OrderjutsuImportPreviewEvent,
    OrderjutsuImportPreviewExtra,
    OrderjutsuImportPreviewIngredient,
    OrderjutsuImportPreviewLayoutSummary,
    OrderjutsuImportPreviewProduct,
    OrderjutsuImportPreviewRecipeRow,
    OrderjutsuImportPreviewStation,
    OrderjutsuImportPreviewStockCandidate,
    OrderjutsuImportPreviewVoucher,
    OrderjutsuImportPreviewWarning,
)
from .stock import upsert_stock_rows
from .vouchers import VOUCHER_KIND_FIXED

IMPORT_NUMBER_PREFIX = "oj:"


class OjImportError(ValueError):
    pass


@dataclass
class OjProduct:
    ref: int
    label: str
    bon_text: str
    price: float
    is_addition: bool
    monitor_stock: bool
    stock: int
    is_voucher: bool


@dataclass
class OjCashier:
    index: int
    label: str
    pin: str
    is_extra: bool
    table_prefix: str | None
    auto_table: bool
    app_layout: dict[str, Any]


@dataclass
class OjStation:
    index: int
    label: str
    printer_loc: str | None
    printer_type: str | None
    products: list[OjProduct]


@dataclass
class OjParsedPayload:
    label: str
    start: datetime
    end: datetime
    currency: str
    app_layout: dict[str, Any]
    cashiers: list[OjCashier]
    stations: list[OjStation]
    product_extras: list[dict[str, int]]
    ingredients: list[dict[str, Any]]
    raw: dict[str, Any]


@dataclass
class OjBomResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    product_refs: set[int] = field(default_factory=set)
    ingredient_refs: set[int] = field(default_factory=set)


def _parse_dt(value: str) -> datetime:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    raise OjImportError(f"Invalid datetime: {value!r}")


def _product_from_raw(raw: dict[str, Any]) -> OjProduct:
    return OjProduct(
        ref=int(raw["ref"]),
        label=str(raw.get("label") or ""),
        bon_text=str(raw.get("bon_text") or raw.get("label") or "").strip(),
        price=float(raw.get("price") or 0),
        is_addition=bool(raw.get("extra")),
        monitor_stock=bool(raw.get("monitor_stock")),
        stock=int(raw.get("stock") or 0),
        is_voucher=bool(raw.get("is_voucher")),
    )


def parse_orderjutsu_payload(payload: dict[str, Any]) -> OjParsedPayload:
    required = ("label", "from", "to", "stations", "cashiers", "app_layout")
    missing = [k for k in required if k not in payload]
    if missing:
        raise OjImportError(f"Missing required keys: {', '.join(missing)}")

    stations: list[OjStation] = []
    for idx, st in enumerate(payload.get("stations") or []):
        products = [_product_from_raw(p) for p in st.get("products") or []]
        stations.append(
            OjStation(
                index=idx,
                label=str(st.get("label") or f"Station {idx + 1}"),
                printer_loc=(str(st.get("printer_loc") or "").strip() or None),
                printer_type=(str(st.get("printer_type") or "").strip() or None),
                products=products,
            )
        )

    cashiers: list[OjCashier] = []
    for idx, c in enumerate(payload.get("cashiers") or []):
        prefix = c.get("table_prefix")
        cashiers.append(
            OjCashier(
                index=idx,
                label=str(c.get("label") or f"Cashier {idx + 1}"),
                pin=str(c.get("key") or "0000"),
                is_extra=bool(c.get("is_extra")),
                table_prefix=(str(prefix).strip() if prefix not in (None, "") else None),
                auto_table=bool(c.get("auto_table")),
                app_layout=c.get("app_layout") or {},
            )
        )

    return OjParsedPayload(
        label=str(payload["label"]).strip(),
        start=_parse_dt(str(payload["from"])),
        end=_parse_dt(str(payload["to"])),
        currency=str(payload.get("currency") or "CHF").strip(),
        app_layout=payload.get("app_layout") or {},
        cashiers=cashiers,
        stations=stations,
        product_extras=list(payload.get("product_extras") or []),
        ingredients=list(payload.get("ingredients") or []),
        raw=payload,
    )


def collect_products(parsed: OjParsedPayload) -> list[OjProduct]:
    by_ref: dict[int, OjProduct] = {}
    for station in parsed.stations:
        for product in station.products:
            by_ref[product.ref] = product
    return list(by_ref.values())


def collect_ingredient_bom(parsed: OjParsedPayload) -> OjBomResult:
    result = OjBomResult()
    for row in parsed.ingredients:
        product_id = int(row["product_id"])
        ingredient_id = int(row["ingredient_id"])
        amount = float(row.get("amount") or 1)
        result.rows.append(
            {"product_id": product_id, "ingredient_id": ingredient_id, "amount": amount}
        )
        result.product_refs.add(product_id)
        result.ingredient_refs.add(ingredient_id)
    return result


def _layout_refs(layout: dict[str, Any]) -> set[int]:
    refs: set[int] = set()
    for row in layout.get("layout") or []:
        for cell in row or []:
            for item in cell.get("items") or []:
                if "ref" in item:
                    refs.add(int(item["ref"]))
    return refs


def collect_sellable_refs(parsed: OjParsedPayload, bom: OjBomResult | None = None) -> set[int]:
    refs: set[int] = set()
    refs |= _layout_refs(parsed.app_layout)
    for cashier in parsed.cashiers:
        refs |= _layout_refs(cashier.app_layout)
    station_refs: set[int] = set()
    for station in parsed.stations:
        for product in station.products:
            if not product.is_voucher and not product.is_addition:
                station_refs.add(product.ref)
    if bom is None:
        bom = collect_ingredient_bom(parsed)
    ingredient_only = bom.ingredient_refs - refs - bom.product_refs
    return refs | (station_refs - ingredient_only)


def _article_label(name: str) -> str:
    text = (name or "").strip()
    return text[:21] if len(text) > 21 else text


def _import_number(ref: int) -> str:
    return f"{IMPORT_NUMBER_PREFIX}{ref}"


def _normalize_match_texts(*values: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = (value or "").strip().lower()
        if not text:
            continue
        for variant in (text, text[:21] if len(text) > 21 else None):
            if variant and variant not in seen:
                seen.add(variant)
                out.append(variant)
    return out


def _article_text_key(text: str, is_addition: bool) -> tuple[str, bool]:
    return (text, bool(is_addition))


def _set_matched_article(entry: dict[str, Any], art: Article) -> None:
    entry["matched_article_id"] = art.id
    entry["matched_article_name"] = art.name
    entry["matched_article_price"] = float(art.price)


def _index_org_articles(
    org_articles: list[Article],
) -> tuple[dict[str, Article], dict[tuple[str, bool], list[Article]]]:
    by_import: dict[str, Article] = {}
    by_key: dict[tuple[str, bool], list[Article]] = {}
    for art in org_articles:
        if art.import_article_number:
            by_import[str(art.import_article_number).strip()] = art
        for text in _normalize_match_texts(art.name, art.label):
            key = _article_text_key(text, art.is_addition)
            bucket = by_key.setdefault(key, [])
            if not any(existing.id == art.id for existing in bucket):
                bucket.append(art)
    return by_import, by_key


def _find_article_matches(
    by_key: dict[tuple[str, bool], list[Article]],
    product: OjProduct,
) -> list[Article]:
    matched: dict[int, Article] = {}
    for text in _normalize_match_texts(product.bon_text, product.label):
        key = _article_text_key(text, product.is_addition)
        for art in by_key.get(key, []):
            matched[art.id] = art
    return list(matched.values())


def suggest_article_matches(
    db: Session,
    organisation_id: int,
    products: list[OjProduct],
    *,
    sellable_refs: set[int],
    composite_refs: set[int],
) -> list[dict[str, Any]]:
    org_articles = (
        db.query(Article)
        .join(ArticleCategory, Article.article_category_id == ArticleCategory.id)
        .filter(ArticleCategory.organisation_id == organisation_id)
        .all()
    )
    by_import, by_key = _index_org_articles(org_articles)

    out: list[dict[str, Any]] = []

    for product in products:
        ingredient_only = product.ref not in sellable_refs and not product.is_voucher
        entry: dict[str, Any] = {
            "ref": product.ref,
            "label": product.label,
            "bon_text": product.bon_text,
            "price": product.price,
            "is_addition": product.is_addition,
            "monitor_stock": product.monitor_stock,
            "stock": product.stock,
            "is_voucher": product.is_voucher,
            "ingredient_only": ingredient_only,
            "is_composite": product.ref in composite_refs,
            "match_kind": "none",
            "matched_article_id": None,
            "matched_article_name": None,
            "matched_article_price": None,
            "ambiguous_article_ids": [],
        }
        if product.is_voucher or ingredient_only:
            out.append(entry)
            continue

        imp = by_import.get(_import_number(product.ref))
        if imp:
            entry["match_kind"] = "import_number"
            _set_matched_article(entry, imp)
            out.append(entry)
            continue

        matches = _find_article_matches(by_key, product)
        if len(matches) == 1:
            entry["match_kind"] = "exact"
            _set_matched_article(entry, matches[0])
        elif len(matches) > 1:
            entry["match_kind"] = "ambiguous"
            entry["ambiguous_article_ids"] = [m.id for m in matches]
        out.append(entry)
    return out


def suggest_ingredient_matches(
    db: Session,
    organisation_id: int,
    ingredient_refs: set[int],
    products_by_ref: dict[int, OjProduct],
) -> list[dict[str, Any]]:
    org_ings = db.query(Ingredient).filter(Ingredient.organisation_id == organisation_id).all()
    by_name = {i.name.strip().lower(): i for i in org_ings}
    out: list[dict[str, Any]] = []
    for ref in sorted(ingredient_refs):
        product = products_by_ref.get(ref)
        bon_text = product.bon_text if product else f"Ingredient {ref}"
        key = bon_text.strip().lower()
        match = by_name.get(key)
        out.append(
            {
                "ref": ref,
                "bon_text": bon_text,
                "match_kind": "exact" if match else "none",
                "matched_ingredient_id": match.id if match else None,
                "matched_ingredient_name": match.name if match else None,
            }
        )
    return out


def suggest_waiter_matches(db: Session, organisation_id: int, cashiers: list[OjCashier]) -> list[dict[str, Any]]:
    waiters = db.query(Waiter).filter(Waiter.organisation_id == organisation_id).all()
    by_name = {w.name.strip().lower(): w for w in waiters}
    out: list[dict[str, Any]] = []
    for cashier in cashiers:
        key = cashier.label.strip().lower()
        match = by_name.get(key)
        layout = cashier.app_layout or {}
        size = layout.get("size") or {}
        has_layout = int(size.get("rows") or 0) > 0 and int(size.get("cols") or 0) > 0
        out.append(
            {
                "index": cashier.index,
                "label": cashier.label,
                "pin": cashier.pin,
                "is_extra": cashier.is_extra,
                "table_prefix": cashier.table_prefix,
                "has_custom_layout": has_layout,
                "auto_table": cashier.auto_table,
                "match_kind": "exact" if match else "none",
                "matched_waiter_id": match.id if match else None,
                "matched_waiter_name": match.name if match else None,
            }
        )
    return out


def _collect_vouchers(parsed: OjParsedPayload, products_by_ref: dict[int, OjProduct]) -> list[dict[str, Any]]:
    vouchers: dict[int, dict[str, Any]] = {}
    for row in parsed.app_layout.get("vouchers") or []:
        vid = int(row["id"])
        vouchers[vid] = {
            "ref": vid,
            "label": str(row.get("label") or ""),
            "price": abs(float(row.get("price") or 0)),
        }
    for product in products_by_ref.values():
        if product.is_voucher:
            vouchers[product.ref] = {
                "ref": product.ref,
                "label": product.bon_text or product.label,
                "price": abs(float(product.price)),
            }
    return list(vouchers.values())


def _layout_has_grid(layout: dict[str, Any]) -> bool:
    size = layout.get("size") or {}
    return int(size.get("rows") or 0) > 0 and int(size.get("cols") or 0) > 0


def build_preview(db: Session, *, organisation_id: int, payload: dict[str, Any]) -> OrderjutsuImportPreview:
    parsed = parse_orderjutsu_payload(payload)
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise api_error("organisation_not_found", status.HTTP_404_NOT_FOUND)

    products = collect_products(parsed)
    products_by_ref = {p.ref: p for p in products}
    bom = collect_ingredient_bom(parsed)
    sellable = collect_sellable_refs(parsed, bom)
    composite_refs = bom.product_refs

    article_matches = suggest_article_matches(
        db,
        organisation_id,
        products,
        sellable_refs=sellable,
        composite_refs=composite_refs,
    )
    for entry in article_matches:
        entry["is_composite"] = entry["ref"] in composite_refs
        if entry["ref"] not in sellable and not entry["is_voucher"]:
            entry["ingredient_only"] = True

    cashier_matches = suggest_waiter_matches(db, organisation_id, parsed.cashiers)
    ingredient_matches = (
        suggest_ingredient_matches(db, organisation_id, bom.ingredient_refs, products_by_ref)
        if bom.ingredient_refs
        else []
    )

    warnings: list[OrderjutsuImportPreviewWarning] = []
    if parsed.currency.upper() != (org.currency or "CHF").upper():
        warnings.append(
            OrderjutsuImportPreviewWarning(
                code="currency_mismatch",
                message=f"Export currency {parsed.currency} differs from organisation currency {org.currency}",
            )
        )

    ambiguous = [p for p in article_matches if p["match_kind"] == "ambiguous"]
    if ambiguous:
        warnings.append(
            OrderjutsuImportPreviewWarning(
                code="ambiguous_articles",
                message=f"{len(ambiguous)} article(s) need manual mapping",
            )
        )

    stations = [
        OrderjutsuImportPreviewStation(
            index=st.index,
            label=st.label,
            product_refs=[p.ref for p in st.products if not p.is_voucher],
            printer_loc=st.printer_loc,
            printer_type=st.printer_type,
        )
        for st in parsed.stations
    ]

    layouts: list[OrderjutsuImportPreviewLayoutSummary] = []
    if _layout_has_grid(parsed.app_layout):
        size = parsed.app_layout.get("size") or {}
        cell_count = sum(
            1
            for row in parsed.app_layout.get("layout") or []
            for cell in row or []
        )
        layouts.append(
            OrderjutsuImportPreviewLayoutSummary(
                name="Standard",
                grid_width=int(size.get("cols") or 1),
                grid_height=int(size.get("rows") or 1),
                cell_count=cell_count,
                is_default=True,
            )
        )
    for cashier in parsed.cashiers:
        if _layout_has_grid(cashier.app_layout):
            size = cashier.app_layout.get("size") or {}
            cell_count = sum(
                1
                for row in cashier.app_layout.get("layout") or []
                for cell in row or []
            )
            layouts.append(
                OrderjutsuImportPreviewLayoutSummary(
                    name=cashier.label,
                    grid_width=int(size.get("cols") or 1),
                    grid_height=int(size.get("rows") or 1),
                    cell_count=cell_count,
                    is_default=False,
                    source_cashier_index=cashier.index,
                )
            )

    extras = [
        OrderjutsuImportPreviewExtra(
            product_ref=int(row["product_id"]),
            extra_ref=int(row["extra_id"]),
        )
        for row in parsed.product_extras
    ]

    voucher_rows = _collect_vouchers(parsed, products_by_ref)

    stock_candidates: list[OrderjutsuImportPreviewStockCandidate] = []
    for product in products:
        if product.is_voucher:
            continue
        if product.ref in composite_refs:
            if product.ref in bom.ingredient_refs:
                stock_candidates.append(
                    OrderjutsuImportPreviewStockCandidate(
                        ref=product.ref,
                        bon_text=product.bon_text,
                        monitor_stock=product.monitor_stock,
                        stock=product.stock,
                        kind="ingredient",
                    )
                )
            continue
        if product.monitor_stock or product.stock != 9999:
            stock_candidates.append(
                OrderjutsuImportPreviewStockCandidate(
                    ref=product.ref,
                    bon_text=product.bon_text,
                    monitor_stock=product.monitor_stock,
                    stock=product.stock,
                    kind="article",
                )
            )

    recipe_rows = [
        OrderjutsuImportPreviewRecipeRow(
            product_ref=int(row["product_id"]),
            product_bon_text=products_by_ref.get(int(row["product_id"]), OjProduct(0, "", "", 0, False, False, 0, False)).bon_text,
            ingredient_ref=int(row["ingredient_id"]),
            ingredient_bon_text=products_by_ref.get(int(row["ingredient_id"]), OjProduct(0, "", "", 0, False, False, 0, False)).bon_text,
            amount=float(row.get("amount") or 1),
        )
        for row in bom.rows
    ]

    has_cash_registers = any(
        c["has_custom_layout"] or c["auto_table"] for c in cashier_matches
    )

    return OrderjutsuImportPreview(
        event=OrderjutsuImportPreviewEvent(
            name=parsed.label,
            start=parsed.start,
            end=parsed.end,
            currency=parsed.currency,
            currency_matches_org=parsed.currency.upper() == (org.currency or "CHF").upper(),
        ),
        products=[OrderjutsuImportPreviewProduct(**m) for m in article_matches],
        cashiers=[OrderjutsuImportPreviewCashier(**m) for m in cashier_matches],
        stations=stations,
        layouts=layouts,
        product_extras=extras,
        stock_candidates=stock_candidates,
        vouchers=[OrderjutsuImportPreviewVoucher(**v) for v in voucher_rows],
        has_ingredients=bool(bom.rows),
        ingredients_enabled=bool(org.ingredients_enabled),
        will_enable_ingredients=bool(bom.rows) and not bool(org.ingredients_enabled),
        ingredient_matches=[OrderjutsuImportPreviewIngredient(**m) for m in ingredient_matches],
        recipe_rows=recipe_rows,
        has_vouchers=bool(voucher_rows),
        has_cash_registers=has_cash_registers,
        warnings=warnings,
    )


def _create_article(
    db: Session,
    *,
    organisation_id: int,
    category_id: int,
    product: OjProduct,
) -> Article:
    art = Article(
        name=product.bon_text,
        label=_article_label(product.bon_text),
        price=product.price,
        import_article_number=_import_number(product.ref),
        is_addition=product.is_addition,
        is_active=True,
        article_category_id=category_id,
    )
    db.add(art)
    db.flush()
    return art


def _create_ingredient(db: Session, *, organisation_id: int, name: str) -> Ingredient:
    ing = Ingredient(name=name.strip(), organisation_id=organisation_id, unit=None, is_active=True)
    db.add(ing)
    db.flush()
    return ing


def _create_waiter(db: Session, *, organisation_id: int, name: str, pin: str) -> Waiter:
    waiter = Waiter(name=name.strip(), pin=pin or "0000", organisation_id=organisation_id)
    db.add(waiter)
    db.flush()
    return waiter


def _build_layout_cells(
    layout: dict[str, Any],
    ref_to_article: dict[int, int],
    voucher_ref_to_uuid: dict[int, str],
    voucher_refs: set[int],
    *,
    addition_refs: set[int] | None = None,
) -> list[SimpleNamespace]:
    additions = addition_refs or set()
    cells: list[SimpleNamespace] = []
    for row_idx, row in enumerate(layout.get("layout") or []):
        for col_idx, cell in enumerate(row or []):
            article_ids: list[int] = []
            voucher_uuids: list[str] = []
            for item in cell.get("items") or []:
                ref = int(item["ref"])
                if ref in additions:
                    continue
                if ref in voucher_refs and ref in voucher_ref_to_uuid:
                    voucher_uuids.append(voucher_ref_to_uuid[ref])
                elif ref in ref_to_article:
                    article_ids.append(ref_to_article[ref])
            if not article_ids and not voucher_uuids:
                continue
            cells.append(
                SimpleNamespace(
                    row=row_idx,
                    col=col_idx,
                    label=str(cell.get("title") or ""),
                    color=str(cell.get("color") or "#eeeeee"),
                    article_ids=article_ids,
                    voucher_definition_uuid=voucher_uuids[0] if voucher_uuids else None,
                    voucher_definition_uuids=voucher_uuids,
                )
            )
    return cells


def commit_orderjutsu_import(
    db: Session,
    commit: OrderjutsuImportCommit,
    payload: dict[str, Any],
) -> Event:
    parsed = parse_orderjutsu_payload(payload)
    org = db.query(Organisation).filter(Organisation.id == commit.organisation_id).first()
    if not org:
        raise api_error("organisation_not_found", status.HTTP_404_NOT_FOUND)

    products = collect_products(parsed)
    products_by_ref = {p.ref: p for p in products}
    bom = collect_ingredient_bom(parsed)
    sellable = collect_sellable_refs(parsed, bom)
    voucher_rows = _collect_vouchers(parsed, products_by_ref)
    voucher_refs = {v["ref"] for v in voucher_rows}
    addition_refs = {p.ref for p in products if p.is_addition}

    if bom.rows and commit.enable_ingredients:
        org.ingredients_enabled = True
        db.flush()

    ref_to_article: dict[int, int] = {}
    article_actions = {a.ref: a for a in commit.articles}
    for product in products:
        if product.is_voucher:
            continue
        action = article_actions.get(product.ref)
        if product.ref not in sellable:
            continue
        if action is None or action.action == "skip":
            continue
        if action.action == "link_existing":
            if not action.article_id:
                raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT)
            ref_to_article[product.ref] = action.article_id
        elif action.action == "create_new":
            art = _create_article(
                db,
                organisation_id=org.id,
                category_id=commit.default_article_category_id,
                product=product,
            )
            ref_to_article[product.ref] = art.id

    ref_to_ingredient: dict[int, int] = {}
    ingredient_actions = {i.ref: i for i in commit.ingredients}
    for ref in bom.ingredient_refs:
        product = products_by_ref.get(ref)
        name = product.bon_text if product else f"Ingredient {ref}"
        action = ingredient_actions.get(ref)
        if action and action.action == "link_existing" and action.ingredient_id:
            ref_to_ingredient[ref] = action.ingredient_id
        else:
            ing = _create_ingredient(db, organisation_id=org.id, name=name)
            ref_to_ingredient[ref] = ing.id

    has_cash_registers = any(
        _layout_has_grid(c.app_layout) or c.auto_table for c in parsed.cashiers
    )
    event = Event(
        name=commit.event.name.strip(),
        status="config",
        start=commit.event.start,
        end=commit.event.end,
        organisation_id=org.id,
        payment_mode="pay_later",
        payment_types=["cash"],
        cash_registers_enabled=commit.event.cash_registers_enabled
        if commit.event.cash_registers_enabled is not None
        else has_cash_registers,
        vouchers_enabled=commit.event.vouchers_enabled
        if commit.event.vouchers_enabled is not None
        else (commit.import_vouchers and bool(voucher_rows)),
    )
    apply_instant_collective_bill_settings(
        event,
        payment_mode=event.payment_mode,
        instant_collective_bill_name=None,
        payment_mode_set=True,
        instant_collective_bill_name_set=False,
    )
    copy_receipt_printing_from_organisation(org, event)
    db.add(event)
    db.flush()

    cashier_actions = {c.index: c for c in commit.cashiers}
    event_waiters: list[SimpleNamespace] = []
    for cashier in parsed.cashiers:
        action = cashier_actions.get(cashier.index)
        if action and action.action == "skip":
            continue
        source_waiter_id = None
        name = cashier.label
        pin = cashier.pin
        if action:
            if action.action == "link_existing" and action.waiter_id:
                source_waiter_id = action.waiter_id
                waiter = db.query(Waiter).filter(Waiter.id == action.waiter_id).first()
                if waiter:
                    name = waiter.name
                    pin = waiter.pin
            elif action.action == "create_org_waiter":
                waiter = _create_waiter(db, organisation_id=org.id, name=cashier.label, pin=cashier.pin)
                source_waiter_id = waiter.id
        event_waiters.append(
            SimpleNamespace(
                uuid=None,
                name=name,
                pin=pin,
                source_waiter_id=source_waiter_id,
                subsidiary_code=None,
            )
        )

    stations_in: list[SimpleNamespace] = []
    station_actions = {s.index: s for s in commit.stations}
    for station in parsed.stations:
        action = station_actions.get(station.index, SimpleNamespace(printer_appliance_id=None))
        article_ids = [
            ref_to_article[p.ref]
            for p in station.products
            if p.ref in ref_to_article and not p.is_voucher and not p.is_addition
        ]
        stations_in.append(
            SimpleNamespace(
                uuid=None,
                name=station.label,
                printer_appliance_id=getattr(action, "printer_appliance_id", None),
                article_ids=sorted(set(article_ids)),
                printer_rules=[],
            )
        )

    voucher_ref_to_uuid: dict[int, str] = {}
    vouchers_in: list[SimpleNamespace] = []
    if commit.import_vouchers and voucher_rows:
        for voucher in voucher_rows:
            new_uuid = str(uuid.uuid4())
            voucher_ref_to_uuid[voucher["ref"]] = new_uuid
            vouchers_in.append(
                SimpleNamespace(
                    uuid=new_uuid,
                    name=voucher["label"],
                    kind=VOUCHER_KIND_FIXED,
                    value_cents=int(round(float(voucher["price"]) * 100)),
                    allowed_article_ids=[],
                    include_additions=True,
                )
            )

    layouts_in: list[SimpleNamespace] = []
    layout_uuid_by_name: dict[str, str] = {}
    if _layout_has_grid(parsed.app_layout):
        layout_uuid = str(uuid.uuid4())
        layout_uuid_by_name["Standard"] = layout_uuid
        size = parsed.app_layout.get("size") or {}
        layouts_in.append(
            SimpleNamespace(
                uuid=layout_uuid,
                name="Standard",
                is_default=True,
                grid_width=int(size.get("cols") or 1),
                grid_height=int(size.get("rows") or 1),
                cells=_build_layout_cells(
                    parsed.app_layout,
                    ref_to_article,
                    voucher_ref_to_uuid,
                    voucher_refs,
                    addition_refs=addition_refs,
                ),
            )
        )

    cash_registers_in: list[SimpleNamespace] = []
    register_index = 0
    for cashier in parsed.cashiers:
        if not (_layout_has_grid(cashier.app_layout) or cashier.auto_table):
            continue
        if _layout_has_grid(cashier.app_layout):
            layout_uuid = str(uuid.uuid4())
            size = cashier.app_layout.get("size") or {}
            layouts_in.append(
                SimpleNamespace(
                    uuid=layout_uuid,
                    name=cashier.label,
                    is_default=False,
                    grid_width=int(size.get("cols") or 1),
                    grid_height=int(size.get("rows") or 1),
                    cells=_build_layout_cells(
                        cashier.app_layout,
                        ref_to_article,
                        voucher_ref_to_uuid,
                        voucher_refs,
                        addition_refs=addition_refs,
                    ),
                )
            )
            layout_uuid_by_name[cashier.label] = layout_uuid
        else:
            layout_uuid = layout_uuid_by_name.get("Standard")
            if not layout_uuid:
                raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT)
        prefix = (cashier.table_prefix or chr(65 + (register_index % 26))).strip().upper()[:3] or "A"
        cash_registers_in.append(
            SimpleNamespace(
                uuid=None,
                name=cashier.label,
                pickup_code_prefix=prefix,
                pin=cashier.pin,
                layout_uuid=layout_uuid_by_name.get(cashier.label) or layout_uuid_by_name["Standard"],
                receipt_printer_appliance_id=None,
                subsidiary_code=None,
            )
        )
        register_index += 1

    if not layouts_in:
        layout_uuid = str(uuid.uuid4())
        layouts_in.append(
            SimpleNamespace(
                uuid=layout_uuid,
                name="Standard",
                is_default=True,
                grid_width=2,
                grid_height=2,
                cells=[],
            )
        )

    replace_event_configuration(
        db,
        event,
        stations_in=stations_in,
        event_waiters_in=event_waiters,
        app_layouts_in=layouts_in,
        cash_registers_in=cash_registers_in if event.cash_registers_enabled else [],
        voucher_definitions_in=vouchers_in,
        kitchen_monitors_in=[],
    )

    base_ids_with_extras: dict[int, list[dict[str, Any]]] = {}
    for row in parsed.product_extras:
        base_ref = int(row["product_id"])
        extra_ref = int(row["extra_id"])
        base_id = ref_to_article.get(base_ref)
        extra_id = ref_to_article.get(extra_ref)
        if base_id and extra_id:
            base_ids_with_extras.setdefault(base_id, []).append(
                {"addition_article_id": extra_id, "sort_order": len(base_ids_with_extras[base_id]), "preselected": False}
            )
    for base_id, items in base_ids_with_extras.items():
        base = db.query(Article).filter(Article.id == base_id).first()
        if base:
            replace_addition_links(db, base, items)

    if bom.rows and org.ingredients_enabled:
        recipes_by_base: dict[int, list[dict[str, Any]]] = {}
        for row in bom.rows:
            base_id = ref_to_article.get(int(row["product_id"]))
            ing_id = ref_to_ingredient.get(int(row["ingredient_id"]))
            if not base_id or not ing_id:
                continue
            recipes_by_base.setdefault(base_id, []).append(
                {
                    "ingredient_id": ing_id,
                    "amount": row["amount"],
                    "sort_order": len(recipes_by_base[base_id]),
                }
            )
        for base_id, items in recipes_by_base.items():
            base = (
                db.query(Article)
                .options(joinedload(Article.article_category))
                .filter(Article.id == base_id)
                .first()
            )
            if base:
                replace_ingredient_links(db, base, items)

    if commit.import_stock:
        stock_overrides = {s.ref: s for s in commit.stock_articles}
        ing_overrides = {s.ref: s for s in commit.stock_ingredients}
        composite_refs = bom.product_refs
        article_stock_items: list[dict[str, Any]] = []
        for product in products:
            if product.is_voucher or product.ref in composite_refs:
                continue
            if product.ref not in ref_to_article:
                continue
            override = stock_overrides.get(product.ref)
            monitor = product.monitor_stock if override is None or override.monitor_stock is None else override.monitor_stock
            qty = product.stock if override is None or override.in_stock is None else override.in_stock
            initial = qty if override is None or override.initial_in_stock is None else override.initial_in_stock
            if not monitor and qty == 9999:
                continue
            article_stock_items.append(
                {
                    "article_id": ref_to_article[product.ref],
                    "monitor_stock": monitor,
                    "in_stock": qty if monitor else None,
                    "initial_in_stock": initial if monitor else None,
                }
            )
        if article_stock_items:
            upsert_stock_rows(db, event, article_stock_items)

        if org.ingredients_enabled:
            ingredient_stock_items: list[dict[str, Any]] = []
            for ref in bom.ingredient_refs:
                product = products_by_ref.get(ref)
                if not product:
                    continue
                ing_id = ref_to_ingredient.get(ref)
                if not ing_id:
                    continue
                override = ing_overrides.get(ref)
                monitor = product.monitor_stock if override is None or override.monitor_stock is None else override.monitor_stock
                qty = float(product.stock if override is None or override.in_stock is None else override.in_stock)
                initial = qty if override is None or override.initial_in_stock is None else float(override.initial_in_stock)
                if not monitor and int(qty) == 9999:
                    continue
                ingredient_stock_items.append(
                    {
                        "ingredient_id": ing_id,
                        "monitor_stock": monitor,
                        "in_stock": qty if monitor else None,
                        "initial_in_stock": initial if monitor else None,
                    }
                )
            if ingredient_stock_items:
                upsert_ingredient_stock_rows(db, event, ingredient_stock_items)

    db.refresh(event)
    return event
