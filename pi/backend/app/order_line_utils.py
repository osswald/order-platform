"""Shared order line grouping, selection take, and merge helpers."""

from __future__ import annotations

import json

FISCAL_LINE_KEYS = ("order_number", "unit_cents", "article_name", "ordered_at")


def discount_signature(discount) -> str:
    from .pricing import normalize_discount

    d = normalize_discount(discount)
    if not d:
        return ""
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def copy_line_fiscal_fields(src: dict, dest: dict) -> None:
    for key in FISCAL_LINE_KEYS:
        if key in src:
            dest[key] = src[key]
    from .pricing import normalize_discount

    d = normalize_discount(src.get("discount"))
    if d:
        dest["discount"] = d
    src_adds = normalize_additions(src.get("additions"))
    if not src_adds:
        return
    dest_adds = normalize_additions(dest.get("additions"))
    src_by_id = {int(a["article_id"]): a for a in src_adds}
    merged: list[dict] = []
    for add in dest_adds:
        entry = dict(add)
        src_add = src_by_id.get(int(add["article_id"]))
        if src_add:
            for key in ("name", "unit_cents"):
                if key in src_add:
                    entry[key] = src_add[key]
        merged.append(entry)
    dest["additions"] = merged


def normalize_additions(additions: list | None) -> list[dict]:
    out = []
    for add in additions or []:
        if not isinstance(add, dict):
            continue
        aid = add.get("article_id")
        if aid is None:
            continue
        out.append({"article_id": int(aid), "qty": max(1, int(add.get("qty") or 1))})
    return out


def additions_signature(additions: list | None) -> str:
    items = normalize_additions(additions)
    items.sort(key=lambda x: (x["article_id"], x["qty"]))
    return json.dumps(items, separators=(",", ":"))


def line_key(
    article_id,
    note: str,
    additions: list | None = None,
    discount=None,
) -> tuple[int, str, str, str]:
    return (
        int(article_id),
        str(note or ""),
        additions_signature(additions),
        discount_signature(discount),
    )


def _is_voucher_sale(entry: dict) -> bool:
    return str(entry.get("kind") or "") == "voucher_sale"


def selection_key(entry: dict) -> tuple:
    """Unified key for article lines and voucher-sale lines/selections."""
    if _is_voucher_sale(entry):
        return ("voucher_sale", str(entry.get("voucher_definition_uuid") or ""))
    return (
        "article",
        *line_key(
            entry.get("article_id"),
            entry.get("note", ""),
            entry.get("additions"),
            entry.get("discount"),
        ),
    )


def take_selections_from_orders(
    orders: list,
    selections: list[dict],
    *,
    load_payload,
    save_payload,
    transfer_destination: dict | None = None,
) -> list[dict]:
    """Remove selected qty from open orders; return extracted line dicts."""
    need: dict[tuple, int] = {}
    for s in selections:
        need[selection_key(s)] = need.get(selection_key(s), 0) + int(s["qty"])

    moved: list[dict] = []
    for order in orders:
        payload = load_payload(order)
        removed_from_order: list[dict] = []
        open_lines: list[dict] = []
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            is_voucher = _is_voucher_sale(line)
            aid = line.get("article_id")
            if aid is None and not is_voucher:
                continue
            note = str(line.get("note") or "")
            adds = normalize_additions(line.get("additions"))
            key = selection_key({**line, "additions": adds})
            qty = max(1, int(line.get("qty") or 1))
            take = min(qty, need.get(key, 0))
            if take > 0:
                if is_voucher:
                    pl = {
                        "kind": "voucher_sale",
                        "voucher_definition_uuid": str(line.get("voucher_definition_uuid") or ""),
                        "qty": take,
                        "note": note,
                        "additions": adds,
                    }
                    for extra in ("voucher_name", "value_cents"):
                        if line.get(extra) is not None:
                            pl[extra] = line[extra]
                else:
                    pl = {
                        "article_id": int(aid),
                        "qty": take,
                        "note": note,
                        "additions": adds,
                    }
                su = line.get("station_uuid")
                if su:
                    pl["station_uuid"] = su
                copy_line_fiscal_fields(line, pl)
                moved.append(pl)
                removed_from_order.append(pl)
                need[key] = need.get(key, 0) - take
                qty -= take
            if qty > 0:
                open_lines.append({**line, "qty": qty, "additions": adds})
        payload["lines"] = open_lines
        if transfer_destination and removed_from_order:
            events = list(payload.get("transfer_events") or [])
            events.append({**transfer_destination, "lines": removed_from_order})
            payload["transfer_events"] = events
        save_payload(order, payload)

    leftover = sum(v for v in need.values() if v > 0)
    if leftover > 0:
        raise ValueError("Selection exceeds open quantities")
    return moved


def merge_lines_into_list(lines: list[dict], incoming: list[dict]) -> None:
    """Merge incoming lines into lines list by selection_key (in-place)."""
    for inc in incoming:
        if not isinstance(inc, dict):
            continue
        aid = inc.get("article_id")
        if aid is None and not _is_voucher_sale(inc):
            continue
        adds = normalize_additions(inc.get("additions"))
        key = selection_key({**inc, "additions": adds})
        qty = max(1, int(inc.get("qty") or 1))
        found = False
        for i, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            if line.get("article_id") is None and not _is_voucher_sale(line):
                continue
            lk = selection_key(line)
            if lk == key:
                lines[i] = {
                    **line,
                    "qty": max(1, int(line.get("qty") or 1)) + qty,
                    "additions": adds,
                }
                su = inc.get("station_uuid") or line.get("station_uuid")
                if su:
                    lines[i]["station_uuid"] = su
                found = True
                break
        if not found:
            lines.append({**inc, "qty": qty, "additions": adds})
