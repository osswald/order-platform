"""Event voucher helpers for Pi edge API."""

from __future__ import annotations

import json

from fastapi import HTTPException

from .pricing import line_total_cents, voucher_entitlement_credit_cents

VOUCHER_KIND_FIXED = "fixed_amount"
VOUCHER_KIND_ARTICLE = "article_entitlement"


def voucher_definitions(ev: dict) -> list[dict]:
    cfg = ev.get("configuration") or {}
    raw = cfg.get("voucher_definitions") or []
    return [d for d in raw if isinstance(d, dict)]


def voucher_definition_by_uuid(ev: dict, v_uuid: str) -> dict | None:
    key = str(v_uuid or "").strip()
    if not key:
        return None
    for d in voucher_definitions(ev):
        if str(d.get("uuid") or "") == key:
            return d
    return None


def is_voucher_sale_line(line: dict) -> bool:
    return isinstance(line, dict) and str(line.get("kind") or "") == "voucher_sale"


def is_article_line(line: dict) -> bool:
    return isinstance(line, dict) and line.get("article_id") is not None and not is_voucher_sale_line(line)


def voucher_sale_unit_cents(ev: dict, line: dict) -> int:
    if line.get("unit_cents") is not None:
        return max(0, int(line["unit_cents"]))
    v_uuid = str(line.get("voucher_definition_uuid") or "").strip()
    vd = voucher_definition_by_uuid(ev, v_uuid)
    if not vd:
        raise HTTPException(status_code=400, detail="Unknown voucher definition on sale line")
    if str(vd.get("kind") or "") != VOUCHER_KIND_FIXED:
        raise HTTPException(status_code=400, detail="Only fixed_amount vouchers can be sold")
    return max(0, int(vd.get("value_cents") or 0))


def line_total_for_order(line: dict, ev: dict, articles: dict) -> int:
    if is_voucher_sale_line(line):
        qty = max(1, int(line.get("qty") or 1))
        return voucher_sale_unit_cents(ev, line) * qty
    return line_total_cents(line, articles)


def order_lines_total_cents(
    lines: list,
    ev: dict,
    articles: dict,
    order_discount: dict | None = None,
) -> tuple[int, int]:
    from .pricing import order_total_cents

    item_count = 0
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        qty = max(1, int(line.get("qty") or 1))
        item_count += qty
    total_cents = order_total_cents(lines, order_discount, ev, articles)
    return total_cents, item_count


def article_lines_only(lines: list) -> list[dict]:
    return [dict(ln) for ln in (lines or []) if is_article_line(ln)]


def selection_matches_entitlement(vd: dict, selection: dict) -> bool:
    allowed = {int(x) for x in (vd.get("allowed_article_ids") or [])}
    aid = int(selection.get("article_id"))
    return aid in allowed


def _normalize_additions(additions: list | None) -> list[dict]:
    out = []
    for add in additions or []:
        if not isinstance(add, dict):
            continue
        aid = add.get("article_id")
        if aid is None:
            continue
        out.append({"article_id": int(aid), "qty": max(1, int(add.get("qty") or 1))})
    return out


def _additions_signature(additions: list | None) -> str:
    items = _normalize_additions(additions)
    items.sort(key=lambda x: (x["article_id"], x["qty"]))
    return json.dumps(items, separators=(",", ":"))


def _line_key(article_id, note: str, additions: list | None = None) -> tuple[int, str, str]:
    return (int(article_id), str(note or ""), _additions_signature(additions))


def compute_voucher_credits(
    ev: dict,
    *,
    gross_cents: int,
    redemptions: list,
    articles: dict,
    selections: list | None = None,
    line_groups: list | None = None,
) -> tuple[int, list[dict]]:
    """Return (total_credit_cents, normalized redemption records)."""
    credits: list[dict] = []
    total_credit = 0
    remaining = gross_cents

    unit_by_key: dict[tuple[int, str, str], int] = {}
    if line_groups:
        for g in line_groups:
            key = _line_key(g["article_id"], g.get("note", ""), g.get("additions"))
            unit_by_key[key] = int(g["unit_cents"])

    for raw in redemptions or []:
        if not isinstance(raw, dict):
            continue
        v_uuid = str(raw.get("voucher_definition_uuid") or "").strip()
        vd = voucher_definition_by_uuid(ev, v_uuid)
        if not vd:
            raise HTTPException(status_code=400, detail="Unknown voucher definition")
        kind = str(vd.get("kind") or "")
        if kind == VOUCHER_KIND_FIXED:
            face = max(0, int(vd.get("value_cents") or 0))
            applied = min(remaining, face)
            if applied <= 0:
                continue
            credits.append(
                {
                    "voucher_definition_uuid": v_uuid,
                    "kind": kind,
                    "applied_cents": applied,
                }
            )
            total_credit += applied
            remaining -= applied
        elif kind == VOUCHER_KIND_ARTICLE:
            sel = raw
            if not selection_matches_entitlement(vd, sel):
                raise HTTPException(status_code=400, detail="Selection not eligible for voucher")
            line_unit: int | None = None
            if selections and line_groups:
                key = _line_key(sel.get("article_id"), sel.get("note", ""), sel.get("additions"))
                line_unit = unit_by_key.get(key)
                if line_unit is None:
                    raise HTTPException(status_code=400, detail="Voucher selection not on open orders")
            applied = voucher_entitlement_credit_cents(
                sel,
                articles,
                vd,
                snapped_line_unit=line_unit,
            )
            credits.append(
                {
                    "voucher_definition_uuid": v_uuid,
                    "kind": kind,
                    "applied_cents": applied,
                    "article_id": int(sel.get("article_id")),
                    "note": str(sel.get("note") or ""),
                    "additions": _normalize_additions(sel.get("additions")),
                }
            )
            total_credit += applied
            remaining = max(0, remaining - applied)
        else:
            raise HTTPException(status_code=400, detail="Unsupported voucher kind")

    return total_credit, credits
