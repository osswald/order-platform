"""Stock validation unit tests."""

import pytest
from app.stock import apply_stock_to_bundle, validate_stock
from fastapi import HTTPException


def test_validate_stock_raises_409_when_insufficient():
    ev = {
        "articles": {
            "10": {
                "id": 10,
                "name": "Bier",
                "monitor_stock": True,
                "in_stock": 2,
            }
        },
        "ingredients": {},
    }
    lines = [{"article_id": 10, "qty": 5}]
    with pytest.raises(HTTPException) as exc_info:
        validate_stock(ev, lines)
    assert exc_info.value.status_code == 409
    detail = exc_info.value.detail
    assert detail["code"] == "stock_insufficient"
    assert detail["issues"][0]["article_name"] == "Bier"
    assert detail["issues"][0]["max_orderable_qty"] == 2


def test_validate_stock_allows_unmonitored_articles():
    ev = {
        "articles": {
            "10": {"id": 10, "name": "Bier", "monitor_stock": False},
        },
        "ingredients": {},
    }
    validate_stock(ev, [{"article_id": 10, "qty": 99}])


def test_validate_stock_allows_when_enough_stock():
    ev = {
        "articles": {
            "10": {"id": 10, "name": "Bier", "monitor_stock": True, "in_stock": 10},
        },
        "ingredients": {},
    }
    validate_stock(ev, [{"article_id": 10, "qty": 3}])


def test_validate_stock_composite_ingredient_shortfall():
    ev = {
        "articles": {
            "10": {
                "id": 10,
                "name": "Pizza",
                "ingredients": [{"ingredient_id": 1, "amount": 1, "name": "Teig"}],
            }
        },
        "ingredients": {
            "1": {"id": 1, "name": "Teig", "monitor_stock": True, "in_stock": 1},
        },
    }
    with pytest.raises(HTTPException) as exc_info:
        validate_stock(ev, [{"article_id": 10, "qty": 3}])
    assert exc_info.value.detail["issues"][0]["reason"] == "ingredient"


def test_apply_stock_deducts_ingredients():
    bundle = {
        "events": [
            {
                "id": 1,
                "articles": {
                    "10": {
                        "id": 10,
                        "name": "Pizza",
                        "ingredients": [{"ingredient_id": 1, "amount": 0.5}],
                    }
                },
                "ingredients": {
                    "1": {"id": 1, "name": "Teig", "monitor_stock": True, "in_stock": 2.0},
                },
            }
        ]
    }
    patch = apply_stock_to_bundle(bundle, 1, [{"article_id": 10, "qty": 2}])
    assert patch["ingredients"]["1"]["in_stock"] == 1.0


def test_apply_stock_deducts_addition_ingredients():
    bundle = {
        "events": [
            {
                "id": 1,
                "articles": {
                    "10": {"id": 10, "name": "Burger"},
                    "20": {
                        "id": 20,
                        "name": "Extra Käse",
                        "is_addition": True,
                        "ingredients": [{"ingredient_id": 1, "amount": 0.5}],
                    },
                },
                "ingredients": {
                    "1": {"id": 1, "name": "Käse", "monitor_stock": True, "in_stock": 3.0},
                },
            }
        ]
    }
    patch = apply_stock_to_bundle(
        bundle,
        1,
        [{"article_id": 10, "qty": 2, "additions": [{"article_id": 20, "qty": 1}]}],
    )
    assert patch["ingredients"]["1"]["in_stock"] == 2.0


def test_apply_stock_strict_raises_when_insufficient():
    bundle = {
        "events": [
            {
                "id": 1,
                "articles": {
                    "10": {
                        "id": 10,
                        "name": "Bier",
                        "monitor_stock": True,
                        "in_stock": 2,
                    }
                },
                "ingredients": {},
            }
        ]
    }
    with pytest.raises(HTTPException) as exc_info:
        apply_stock_to_bundle(bundle, 1, [{"article_id": 10, "qty": 5}], strict=True)
    assert exc_info.value.status_code == 409


def test_apply_stock_non_strict_clamps_when_insufficient():
    bundle = {
        "events": [
            {
                "id": 1,
                "articles": {
                    "10": {
                        "id": 10,
                        "name": "Bier",
                        "monitor_stock": True,
                        "in_stock": 2,
                    }
                },
                "ingredients": {},
            }
        ]
    }
    patch = apply_stock_to_bundle(bundle, 1, [{"article_id": 10, "qty": 5}], strict=False)
    assert patch["articles"]["10"]["in_stock"] == 0


def test_validate_stock_shared_ingredient_across_lines():
    ev = {
        "articles": {
            "10": {
                "id": 10,
                "name": "Kartoffelsalat",
                "ingredients": [{"ingredient_id": 1, "amount": 1, "name": "Kartoffelsalat"}],
            },
            "11": {"id": 11, "name": "Cervelat"},
            "20": {
                "id": 20,
                "name": "mit Kartoffelsalat",
                "is_addition": True,
                "ingredients": [{"ingredient_id": 1, "amount": 0.5, "name": "Kartoffelsalat"}],
            },
        },
        "ingredients": {
            "1": {"id": 1, "name": "Kartoffelsalat", "monitor_stock": True, "in_stock": 30},
        },
    }
    lines = [
        {"article_id": 10, "qty": 29, "additions": []},
        {"article_id": 11, "qty": 3, "additions": [{"article_id": 20, "qty": 1}]},
    ]
    with pytest.raises(HTTPException) as exc_info:
        validate_stock(ev, lines)
    assert exc_info.value.status_code == 409
    issues = exc_info.value.detail["issues"]
    assert any(i.get("line_index") == -1 and i.get("reason") == "ingredient" for i in issues)
