"""Event voucher definitions validation and edge redemption ingestion."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import status
from .i18n.errors import api_error
from sqlalchemy.orm import Session

from .models import Article, ArticleCategory, Event, EventVoucherDefinition, EventVoucherRedemption

VOUCHER_KIND_FIXED = "fixed_amount"
VOUCHER_KIND_ARTICLE = "article_entitlement"
VOUCHER_KINDS = {VOUCHER_KIND_FIXED, VOUCHER_KIND_ARTICLE}


def assert_voucher_definition_in(event: Event, vd: Any) -> None:
    kind = str(getattr(vd, "kind", "") or "").strip()
    if kind not in VOUCHER_KINDS:
        raise api_error("invalid_voucher_kind", status.HTTP_422_UNPROCESSABLE_ENTITY, kind=kind)
    name = str(getattr(vd, "name", "") or "").strip()
    if not name:
        raise api_error("voucher_name_required", status.HTTP_422_UNPROCESSABLE_ENTITY)
    value_cents = getattr(vd, "value_cents", None)
    if kind == VOUCHER_KIND_FIXED:
        if value_cents is None or int(value_cents) < 1:
            raise api_error("voucher_fixed_amount_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)
    else:
        allowed = list(getattr(vd, "allowed_article_ids", None) or [])
        if not allowed:
            raise api_error("voucher_article_entitlement_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)


def assert_voucher_articles_in_org(db: Session, event: Event, article_ids: list[int]) -> None:
    if not article_ids:
        return
    org_id = event.organisation_id
    count = (
        db.query(Article.id)
        .join(ArticleCategory, Article.article_category_id == ArticleCategory.id)
        .filter(
            Article.id.in_(list(set(article_ids))),
            ArticleCategory.organisation_id == org_id,
            Article.is_addition.is_(False),
        )
        .distinct()
        .count()
    )
    if count != len(set(article_ids)):
        raise api_error("voucher_articles_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)


def normalize_cell_voucher_uuids(cell) -> list[str]:
    """Merge voucher_definition_uuids list and legacy single uuid from payload or ORM."""
    uuids: list[str] = []
    raw_list = getattr(cell, "voucher_definition_uuids", None)
    if isinstance(raw_list, list):
        for x in raw_list:
            s = str(x or "").strip()
            if s and s not in uuids:
                uuids.append(s)
    legacy = str(getattr(cell, "voucher_definition_uuid", "") or "").strip()
    if legacy and legacy not in uuids:
        uuids.append(legacy)
    return uuids


def cell_voucher_uuids_for_read(orm_cell) -> list[str]:
    raw = getattr(orm_cell, "voucher_definition_uuids", None) or []
    uuids: list[str] = []
    if isinstance(raw, list):
        for x in raw:
            s = str(x or "").strip()
            if s and s not in uuids:
                uuids.append(s)
    if not uuids:
        legacy = str(getattr(orm_cell, "voucher_definition_uuid", "") or "").strip()
        if legacy:
            uuids.append(legacy)
    return uuids


def voucher_definitions_by_uuid(definitions: list) -> dict[str, Any]:
    return {
        str(getattr(d, "uuid", "") or "").strip(): d
        for d in definitions
        if str(getattr(d, "uuid", "") or "").strip()
    }


def assert_layout_cells_vouchers(
    db: Session,
    event: Event,
    layouts_payload: list,
    vouchers_payload: list,
) -> None:
    by_uuid = voucher_definitions_by_uuid(vouchers_payload)
    for layout in layouts_payload:
        for cell in layout.cells:
            article_ids = list(getattr(cell, "article_ids", None) or [])
            v_uuids = normalize_cell_voucher_uuids(cell)
            if not v_uuids and not article_ids:
                raise api_error("layout_cell_requires_content", status.HTTP_422_UNPROCESSABLE_ENTITY, row=cell.row, col=cell.col)
            for v_uuid in v_uuids:
                vd = by_uuid.get(v_uuid)
                if not vd:
                    raise api_error("unknown_voucher_on_cell", status.HTTP_422_UNPROCESSABLE_ENTITY, row=cell.row, col=cell.col)
                if str(getattr(vd, "kind", "")) != VOUCHER_KIND_FIXED:
                    raise api_error("only_fixed_amount_on_cell", status.HTTP_422_UNPROCESSABLE_ENTITY)


def persist_voucher_redemptions_from_payload(
    db: Session,
    *,
    event_id: int,
    payment_client_order_id: str,
    redemptions: list,
) -> None:
    if not redemptions:
        return
    for raw in redemptions:
        if not isinstance(raw, dict):
            continue
        v_uuid = str(raw.get("voucher_definition_uuid") or "").strip()
        if not v_uuid:
            continue
        db.add(
            EventVoucherRedemption(
                uuid=str(raw.get("uuid") or uuid.uuid4()),
                event_id=event_id,
                voucher_definition_uuid=v_uuid,
                payment_client_order_id=payment_client_order_id,
                kind=str(raw.get("kind") or ""),
                applied_cents=int(raw.get("applied_cents") or 0),
                article_id=raw.get("article_id"),
                note=raw.get("note"),
                additions=raw.get("additions"),
            )
        )


def replace_event_voucher_definitions(db: Session, event: Event, vouchers_in: list) -> None:
    existing = {
        v.uuid: v
        for v in db.query(EventVoucherDefinition).filter(EventVoucherDefinition.event_id == event.id).all()
    }
    kept: set[str] = set()
    for idx, vd_in in enumerate(vouchers_in):
        assert_voucher_definition_in(event, vd_in)
        allowed = list(getattr(vd_in, "allowed_article_ids", None) or [])
        assert_voucher_articles_in_org(db, event, allowed)
        v_uuid = (getattr(vd_in, "uuid", None) or "").strip() or None
        row = existing.get(v_uuid) if v_uuid else None
        kind = str(getattr(vd_in, "kind", "") or "").strip()
        value_cents = int(vd_in.value_cents) if kind == VOUCHER_KIND_FIXED else None
        if row is None:
            row = EventVoucherDefinition(
                event_id=event.id,
                uuid=v_uuid or str(uuid.uuid4()),
                name=str(vd_in.name).strip(),
                kind=kind,
                value_cents=value_cents,
                allowed_article_ids=allowed,
                include_additions=bool(getattr(vd_in, "include_additions", True)),
                sort_order=idx,
            )
            db.add(row)
        else:
            row.name = str(vd_in.name).strip()
            row.kind = kind
            row.value_cents = value_cents
            row.allowed_article_ids = allowed
            row.include_additions = bool(getattr(vd_in, "include_additions", True))
            row.sort_order = idx
        kept.add(row.uuid)
    for v_uuid, row in list(existing.items()):
        if v_uuid not in kept:
            db.delete(row)
