"""Line pricing including article additions."""

from __future__ import annotations


def _article_entry(articles: dict, article_id) -> dict | None:
    return articles.get(str(article_id)) or articles.get(article_id)


def addition_display_name(
    addition: dict,
    articles: dict,
    base_article: dict | None = None,
) -> str:
    """Kitchen-slip label for a Zusatz (prefer bundle `label` over internal `name`)."""
    aid = addition.get("article_id")
    if aid is None:
        return "Zusatz"
    aid_n = int(aid)
    label = str(addition.get("label") or "").strip()
    if label:
        return label
    name = str(addition.get("name") or "").strip()
    if name:
        return name
    if base_article:
        for entry in base_article.get("additions") or []:
            if not isinstance(entry, dict):
                continue
            if int(entry.get("article_id") or 0) != aid_n:
                continue
            entry_label = str(entry.get("label") or "").strip()
            if entry_label:
                return entry_label
            entry_name = str(entry.get("name") or "").strip()
            if entry_name:
                return entry_name
    add_art = _article_entry(articles, aid_n)
    if add_art:
        art_label = str(add_art.get("label") or "").strip()
        if art_label:
            return art_label
        art_name = str(add_art.get("name") or "").strip()
        if art_name:
            return art_name
    return f"Zusatz #{aid_n}"


def _addition_price_cents(articles: dict, base_article: dict | None, addition_id: int) -> int:
    if base_article:
        for add in base_article.get("additions") or []:
            if int(add.get("article_id")) == int(addition_id):
                return int(round(float(add.get("price", 0)) * 100))
    a = _article_entry(articles, addition_id)
    if a and a.get("price") is not None:
        return int(round(float(a["price"]) * 100))
    return 0


def line_unit_cents(line: dict, articles: dict) -> int:
    # Snapshotted lines store unit_cents as the full per-unit price (base + additions).
    if line.get("unit_cents") is not None:
        return max(0, int(line["unit_cents"]))
    aid = line.get("article_id")
    base = _article_entry(articles, aid)
    price = float(base["price"]) if base and base.get("price") is not None else 0.0
    unit = int(round(price * 100))
    for add in line.get("additions") or []:
        if not isinstance(add, dict):
            continue
        add_id = add.get("article_id")
        if add_id is None:
            continue
        add_qty = max(1, int(add.get("qty") or 1))
        if add.get("unit_cents") is not None:
            unit += int(add["unit_cents"]) * add_qty
        else:
            unit += _addition_price_cents(articles, base, int(add_id)) * add_qty
    return max(0, unit)


def line_total_cents(line: dict, articles: dict) -> int:
    qty = max(1, int(line.get("qty") or 1))
    return line_unit_cents(line, articles) * qty
