"""Synthetic basket generation for Pi admin load-test bursts."""

from __future__ import annotations

import random
from typing import Any

ADDITION_ATTACH_PROBABILITY = 0.5
PRESELECTED_WEIGHT = 3
UNSELECTED_WEIGHT = 1


def _article_map(event: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = event.get("articles") or {}
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items() if isinstance(v, dict)}
    return {}


def _is_sellable_base(article: dict[str, Any] | None) -> bool:
    if not article:
        return False
    if article.get("is_addition") is True:
        return False
    if article.get("sellable") is False:
        return False
    # Prefer skipping monitored stock that is empty
    if article.get("monitor_stock") and article.get("in_stock") is not None:
        try:
            if int(article.get("in_stock") or 0) <= 0:
                return False
        except (TypeError, ValueError):
            pass
    return True


def build_station_pools(event: dict[str, Any]) -> dict[str, list[int]]:
    """Map station uuid → sellable non-addition article ids."""
    arts = _article_map(event)
    pools: dict[str, list[int]] = {}
    stations = (event.get("configuration") or {}).get("stations") or []
    for station in stations:
        if not isinstance(station, dict):
            continue
        uuid = str(station.get("uuid") or "").strip()
        if not uuid:
            continue
        ids: list[int] = []
        for aid in station.get("article_ids") or []:
            try:
                article_id = int(aid)
            except (TypeError, ValueError):
                continue
            article = arts.get(str(article_id))
            if _is_sellable_base(article):
                ids.append(article_id)
        if ids:
            pools[uuid] = ids
    return pools


def _weighted_sample_without_replacement(
    items: list[dict[str, Any]],
    k: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    remaining = list(items)
    picked: list[dict[str, Any]] = []
    for _ in range(min(k, len(remaining))):
        weights = [
            PRESELECTED_WEIGHT if bool(item.get("preselected")) else UNSELECTED_WEIGHT for item in remaining
        ]
        choice = rng.choices(remaining, weights=weights, k=1)[0]
        picked.append(choice)
        remaining.remove(choice)
    return picked


def _pick_additions(
    article: dict[str, Any],
    rng: random.Random,
    *,
    attach_probability: float = ADDITION_ATTACH_PROBABILITY,
) -> list[dict[str, Any]]:
    additions = [a for a in (article.get("additions") or []) if isinstance(a, dict) and a.get("article_id") is not None]
    if not additions:
        return []
    if rng.random() >= attach_probability:
        return []
    k = rng.randint(1, len(additions))
    chosen = _weighted_sample_without_replacement(additions, k, rng)
    out: list[dict[str, Any]] = []
    for add in chosen:
        try:
            aid = int(add["article_id"])
        except (TypeError, ValueError, KeyError):
            continue
        out.append({"article_id": aid, "qty": 1})
    return out


def generate_basket_lines(
    event: dict[str, Any],
    *,
    rng: random.Random | None = None,
    people: int | None = None,
) -> list[dict[str, Any]]:
    """
    Build merged order lines for 1–8 people from 1..n random stations.

    Returns list of dicts suitable for OrderLineIn: article_id, qty, note, additions.
    """
    rng = rng or random.Random()
    pools = build_station_pools(event)
    if not pools:
        raise ValueError("No sellable station articles available for load-test basket")

    station_ids = list(pools.keys())
    n = rng.randint(1, len(station_ids))
    chosen_stations = rng.sample(station_ids, n)
    article_pool: list[int] = []
    for sid in chosen_stations:
        article_pool.extend(pools[sid])
    # Deduplicate while preserving order
    seen: set[int] = set()
    unique_pool: list[int] = []
    for aid in article_pool:
        if aid not in seen:
            seen.add(aid)
            unique_pool.append(aid)
    if not unique_pool:
        raise ValueError("No sellable station articles available for load-test basket")

    person_count = people if people is not None else rng.randint(1, 8)
    person_count = max(1, min(8, int(person_count)))

    arts = _article_map(event)
    # Accumulate qty by (article_id, additions signature)
    merged: dict[tuple, dict[str, Any]] = {}
    for _ in range(person_count):
        # Each person orders 1–2 articles from the pool
        picks = rng.randint(1, min(2, len(unique_pool)))
        for article_id in rng.sample(unique_pool, picks):
            article = arts.get(str(article_id)) or {}
            additions = _pick_additions(article, rng)
            add_key = tuple(sorted((int(a["article_id"]), int(a.get("qty") or 1)) for a in additions))
            key = (int(article_id), add_key)
            if key not in merged:
                merged[key] = {
                    "article_id": int(article_id),
                    "qty": 0,
                    "note": "",
                    "additions": list(additions),
                }
            merged[key]["qty"] += 1

    return list(merged.values())
