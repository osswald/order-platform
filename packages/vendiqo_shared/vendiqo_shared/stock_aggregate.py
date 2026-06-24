"""Stock quantity aggregation from order lines."""

from __future__ import annotations

from collections import defaultdict


def aggregate_line_qty(lines: list[dict]) -> dict[int, int]:
    totals: dict[int, int] = defaultdict(int)
    for line in lines or []:
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
