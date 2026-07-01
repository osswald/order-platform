"""Tests for ingredient stock aggregation and max-orderable calculations."""

from decimal import Decimal

from vendiqo_shared.ingredient_stock import (
    aggregate_ingredient_deductions,
    cart_ingredient_usage,
    max_orderable_from_ingredients,
    validate_order_stock,
)


def _article_with_ingredients(aid: int, ingredients: list[dict]) -> dict:
    return {"id": aid, "ingredients": ingredients}


def test_aggregate_ingredient_deductions_sums_per_line():
    articles = {
        10: _article_with_ingredients(10, [{"ingredient_id": 1, "amount": 0.3}]),
    }
    lines = [{"article_id": 10, "qty": 2}]
    assert aggregate_ingredient_deductions(lines, articles) == {1: Decimal("0.6")}


def test_aggregate_ingredient_deductions_skips_non_composite():
    articles = {10: {"id": 10}}
    lines = [{"article_id": 10, "qty": 5}]
    assert aggregate_ingredient_deductions(lines, articles) == {}


def test_cart_ingredient_usage_across_lines():
    articles = {
        10: _article_with_ingredients(10, [{"ingredient_id": 1, "amount": 2}]),
        11: _article_with_ingredients(11, [{"ingredient_id": 1, "amount": 1}]),
    }
    lines = [
        {"article_id": 10, "qty": 1},
        {"article_id": 11, "qty": 3},
    ]
    assert cart_ingredient_usage(lines, articles) == {1: Decimal("5")}


def test_max_orderable_from_ingredients_limiting():
    recipe = [{"ingredient_id": 1, "amount": 0.3, "name": "Tomaten"}]
    stock = {1: {"monitor_stock": True, "in_stock": Decimal("1.0"), "name": "Tomaten"}}
    result = max_orderable_from_ingredients(recipe, stock, cart_usage={})
    assert result["max"] == 3
    assert result["limiting_name"] == "Tomaten"


def test_max_orderable_from_ingredients_unmonitored():
    recipe = [{"ingredient_id": 1, "amount": 1, "name": "Salz"}]
    stock = {1: {"monitor_stock": False, "in_stock": None, "name": "Salz"}}
    result = max_orderable_from_ingredients(recipe, stock, cart_usage={})
    assert result["max"] is None


def test_validate_order_stock_returns_issues_for_composite():
    ev = {
        "articles": {
            "10": _article_with_ingredients(
                10,
                [{"ingredient_id": 1, "amount": 1, "name": "Tomaten"}],
            ),
        },
        "ingredients": {
            "1": {
                "id": 1,
                "name": "Tomaten",
                "monitor_stock": True,
                "in_stock": 2,
            },
        },
    }
    lines = [{"article_id": 10, "qty": 5, "additions": []}]
    issues = validate_order_stock(ev, lines)
    assert len(issues) == 1
    assert issues[0]["line_index"] == 0
    assert issues[0]["max_orderable_qty"] == 2
    assert issues[0]["reason"] == "ingredient"


def test_validate_order_stock_article_direct():
    ev = {
        "articles": {
            "10": {"id": 10, "name": "Bier", "monitor_stock": True, "in_stock": 3},
        },
        "ingredients": {},
    }
    lines = [{"article_id": 10, "qty": 5}]
    issues = validate_order_stock(ev, lines)
    assert len(issues) == 1
    assert issues[0]["reason"] == "article"
    assert issues[0]["max_orderable_qty"] == 3


def test_aggregate_ingredient_deductions_includes_additions():
    articles = {
        10: {"id": 10},
        20: _article_with_ingredients(20, [{"ingredient_id": 1, "amount": 0.5}]),
    }
    lines = [{"article_id": 10, "qty": 2, "additions": [{"article_id": 20, "qty": 2}]}]
    assert aggregate_ingredient_deductions(lines, articles) == {1: Decimal("2.0")}


def test_aggregate_ingredient_deductions_base_and_addition_share_ingredient():
    articles = {
        10: _article_with_ingredients(10, [{"ingredient_id": 1, "amount": 1}]),
        20: _article_with_ingredients(20, [{"ingredient_id": 1, "amount": 0.5}]),
    }
    lines = [{"article_id": 10, "qty": 2, "additions": [{"article_id": 20, "qty": 1}]}]
    assert aggregate_ingredient_deductions(lines, articles) == {1: Decimal("3.0")}


def test_validate_order_stock_addition_ingredient_shortfall():
    ev = {
        "articles": {
            "10": {"id": 10, "name": "Burger"},
            "20": _article_with_ingredients(
                20,
                [{"ingredient_id": 1, "amount": 1, "name": "Käse"}],
            ),
        },
        "ingredients": {
            "1": {"id": 1, "name": "Käse", "monitor_stock": True, "in_stock": 2},
        },
    }
    lines = [{"article_id": 10, "qty": 3, "additions": [{"article_id": 20, "qty": 1}]}]
    issues = validate_order_stock(ev, lines)
    assert any(i.get("reason") == "addition_ingredient" for i in issues)


def test_validate_order_stock_shared_ingredient_across_lines():
    ev = {
        "articles": {
            "10": _article_with_ingredients(
                10,
                [{"ingredient_id": 1, "amount": 1, "name": "Kartoffelsalat"}],
            ),
            "11": {"id": 11, "name": "Cervelat"},
            "20": _article_with_ingredients(
                20,
                [{"ingredient_id": 1, "amount": 0.5, "name": "Kartoffelsalat"}],
            ),
        },
        "ingredients": {
            "1": {
                "id": 1,
                "name": "Kartoffelsalat",
                "monitor_stock": True,
                "in_stock": 30,
            },
        },
    }
    lines = [
        {"article_id": 10, "qty": 29, "additions": []},
        {"article_id": 11, "qty": 3, "additions": [{"article_id": 20, "qty": 1}]},
    ]
    issues = validate_order_stock(ev, lines)
    assert len(issues) >= 1
    aggregate = [i for i in issues if i.get("line_index") == -1 and i.get("reason") == "ingredient"]
    assert len(aggregate) == 1
    assert aggregate[0]["limiting_name"] == "Kartoffelsalat"
    assert aggregate[0]["requested_qty"] == 30.5
    assert aggregate[0]["max_orderable_qty"] == 30.0
