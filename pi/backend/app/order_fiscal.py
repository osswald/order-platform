"""Per-event order numbers and fiscal line snapshots."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .order_line_utils import normalize_additions
from .pricing import _addition_price_cents, _article_entry, line_unit_cents


def is_ferdig_client_order_id(client_order_id: str) -> bool:
    return str(client_order_id or "").startswith("pwa-")


def allocate_order_number(db: Session, event_id: int) -> int:
    from .models import EventOrderCounter

    row = db.query(EventOrderCounter).filter(EventOrderCounter.event_id == event_id).first()
    if not row:
        row = EventOrderCounter(event_id=event_id, next_number=1)
        db.add(row)
        db.flush()
    n = int(row.next_number)
    row.next_number = n + 1
    return n


def waiter_name_from_event(ev: dict, waiter_uuid: str | None) -> str | None:
    if not waiter_uuid:
        return None
    for w in (ev.get("configuration") or {}).get("waiters") or []:
        if str(w.get("uuid")) == str(waiter_uuid):
            name = str(w.get("name") or "").strip()
            return name or None
    return None


def _snapshot_additions(additions: list | None, articles: dict, base_article: dict | None) -> list[dict]:
    out: list[dict] = []
    for add in normalize_additions(additions):
        entry = dict(add)
        aid = add["article_id"]
        add_art = _article_entry(articles, aid)
        if add_art and add_art.get("name"):
            entry["name"] = add_art["name"]
        entry["unit_cents"] = _addition_price_cents(articles, base_article, aid)
        out.append(entry)
    return out


def snapshot_line(line: dict, articles: dict, *, order_number: int | None = None) -> dict:
    aid = line.get("article_id")
    base = _article_entry(articles, aid)
    raw = {
        k: v
        for k, v in line.items()
        if k not in ("unit_cents", "article_name")
    }
    snap: dict[str, Any] = dict(raw)
    if base and base.get("name"):
        snap["article_name"] = base["name"]
    snap["unit_cents"] = line_unit_cents(raw, articles)
    snap["additions"] = _snapshot_additions(line.get("additions"), articles, base)
    if order_number is not None:
        snap["order_number"] = order_number
    elif line.get("order_number") is not None:
        snap["order_number"] = int(line["order_number"])
    return snap


def snapshot_lines(lines: list, articles: dict, *, order_number: int | None = None) -> list[dict]:
    out: list[dict] = []
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        out.append(snapshot_line(line, articles, order_number=order_number))
    return out


def distinct_order_numbers_from_payload(payload: dict, *, legacy_key: str) -> set:
    keys: set = set()
    doc = payload.get("order_number")
    lines = payload.get("lines") or []
    found = False
    for line in lines:
        if not isinstance(line, dict):
            continue
        qty = max(1, int(line.get("qty") or 1))
        if qty < 1:
            continue
        n = line.get("order_number")
        if n is not None:
            keys.add(int(n))
            found = True
        elif doc is not None:
            keys.add(int(doc))
            found = True
    if not found:
        keys.add(legacy_key)
    return keys


def distinct_order_numbers_for_local_orders(orders) -> int:
    keys: set = set()
    for o in orders:
        payload = json.loads(o.payload_json)
        keys |= distinct_order_numbers_from_payload(payload, legacy_key=f"legacy:{o.id}")
    return len(keys)


def document_order_number(payload: dict) -> int | None:
    n = payload.get("order_number")
    if n is not None:
        return int(n)
    for line in payload.get("lines") or []:
        if isinstance(line, dict) and line.get("order_number") is not None:
            return int(line["order_number"])
    return None
