"""Shared order line grouping, selection take, and merge helpers."""

from __future__ import annotations

import json

FISCAL_LINE_KEYS = ("order_number", "unit_cents", "article_name", "ordered_at")


def copy_line_fiscal_fields(src: dict, dest: dict) -> None:
    for key in FISCAL_LINE_KEYS:
        if key in src:
            dest[key] = src[key]
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


def line_key(article_id, note: str, additions: list | None = None) -> tuple[int, str, str]:
    return (int(article_id), str(note or ""), additions_signature(additions))


def take_selections_from_orders(
    orders: list,
    selections: list[dict],
    *,
    load_payload,
    save_payload,
    transfer_destination: dict | None = None,
) -> list[dict]:
    """Remove selected qty from open orders; return extracted line dicts."""
    need: dict[tuple[int, str, str], int] = {}
    for s in selections:
        key = line_key(s["article_id"], s.get("note", ""), s.get("additions"))
        need[key] = need.get(key, 0) + int(s["qty"])

    moved: list[dict] = []
    for order in orders:
        payload = load_payload(order)
        removed_from_order: list[dict] = []
        open_lines: list[dict] = []
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            aid = line.get("article_id")
            if aid is None:
                continue
            note = str(line.get("note") or "")
            adds = normalize_additions(line.get("additions"))
            key = line_key(aid, note, adds)
            qty = max(1, int(line.get("qty") or 1))
            take = min(qty, need.get(key, 0))
            if take > 0:
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
    """Merge incoming lines into lines list by line_key (in-place)."""
    for inc in incoming:
        if not isinstance(inc, dict):
            continue
        aid = inc.get("article_id")
        if aid is None:
            continue
        note = str(inc.get("note") or "")
        adds = normalize_additions(inc.get("additions"))
        key = line_key(aid, note, adds)
        qty = max(1, int(inc.get("qty") or 1))
        found = False
        for i, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            lk = line_key(
                line.get("article_id"),
                str(line.get("note") or ""),
                line.get("additions"),
            )
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
