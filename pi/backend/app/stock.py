"""Stock validation and bundle updates (mirrors cloud stock rules)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException


def _aggregate_line_qty(lines: list) -> dict[int, int]:
    totals: dict[int, int] = defaultdict(int)
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        aid = line.get("article_id")
        if aid is None:
            continue
        line_qty = int(line.get("qty") or 0)
        if line_qty > 0:
            totals[int(aid)] += line_qty
        for add in line.get("additions") or []:
            if not isinstance(add, dict):
                continue
            add_id = add.get("article_id")
            if add_id is None:
                continue
            add_qty = max(1, int(add.get("qty") or 1))
            totals[int(add_id)] += line_qty * add_qty
    return dict(totals)


def _article_entry(articles: dict, article_id: int) -> dict | None:
    return articles.get(str(article_id)) or articles.get(article_id)


def _snapshot_fields(monitor_stock: bool, in_stock: int | None) -> dict[str, Any]:
    if not monitor_stock:
        return {"monitor_stock": False, "in_stock": None, "sellable": True}
    qty = in_stock if in_stock is not None else 0
    return {
        "monitor_stock": True,
        "in_stock": qty,
        "sellable": qty > 0,
    }


def validate_stock(ev: dict, lines: list) -> None:
    arts = ev.get("articles") or {}
    totals = _aggregate_line_qty(lines)
    if not totals:
        return
    for aid, need in totals.items():
        a = _article_entry(arts, aid)
        if not a or not a.get("monitor_stock"):
            continue
        available = a.get("in_stock")
        if available is None:
            available = 0
        available = int(available)
        if need > available:
            name = a.get("name") or f"Artikel #{aid}"
            raise HTTPException(
                status_code=409,
                detail=f"Nur noch {available} Stück von «{name}» verfügbar",
            )


def _sync_additions_lists(arts: dict) -> None:
    for base in arts.values():
        if not isinstance(base, dict) or not base.get("additions"):
            continue
        for add in base["additions"]:
            src = _article_entry(arts, add.get("article_id"))
            if not src:
                continue
            for key in ("monitor_stock", "in_stock", "sellable"):
                if key in src:
                    add[key] = src[key]


def apply_stock_to_bundle(bundle: dict, event_id: int, lines: list) -> dict[str, Any]:
    """Decrement monitored articles in bundle; return updated article entries."""
    ev = None
    for e in bundle.get("events", []) or []:
        if int(e.get("id")) == int(event_id):
            ev = e
            break
    if not ev:
        return {}

    arts = ev.setdefault("articles", {})
    totals = _aggregate_line_qty(lines)
    updated: dict[str, Any] = {}

    for aid, need in totals.items():
        key = str(aid)
        a = _article_entry(arts, aid)
        if not a or not a.get("monitor_stock"):
            continue
        current = a.get("in_stock")
        if current is None:
            current = 0
        new_qty = max(0, int(current) - need)
        fields = _snapshot_fields(True, new_qty)
        merged = {**a, **fields}
        arts[key] = merged
        updated[key] = merged

    _sync_additions_lists(arts)
    return updated


def save_bundle(db, bundle: dict) -> None:
    from datetime import datetime, timezone
    import json

    from .models import SyncedBundle

    body = json.dumps(bundle)
    now = datetime.now(timezone.utc)
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    if row:
        row.json_body = body
        row.updated_at = now
    else:
        db.add(SyncedBundle(id=1, json_body=body, updated_at=now))
