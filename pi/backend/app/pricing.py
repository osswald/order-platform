"""Line pricing including article additions."""

from __future__ import annotations


def _article_entry(articles: dict, article_id) -> dict | None:
    return articles.get(str(article_id)) or articles.get(article_id)


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
        unit += _addition_price_cents(articles, base, int(add_id)) * add_qty
    return max(0, unit)


def line_total_cents(line: dict, articles: dict) -> int:
    qty = max(1, int(line.get("qty") or 1))
    return line_unit_cents(line, articles) * qty
