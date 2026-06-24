"""Stock validation unit tests."""

import pytest
from fastapi import HTTPException

from app.stock import validate_stock


def test_validate_stock_raises_409_when_insufficient():
    ev = {
        "articles": {
            "10": {
                "id": 10,
                "name": "Bier",
                "monitor_stock": True,
                "in_stock": 2,
            }
        }
    }
    lines = [{"article_id": 10, "qty": 5}]
    with pytest.raises(HTTPException) as exc_info:
        validate_stock(ev, lines)
    assert exc_info.value.status_code == 409
    assert "Bier" in str(exc_info.value.detail)
    assert "2" in str(exc_info.value.detail)


def test_validate_stock_allows_unmonitored_articles():
    ev = {
        "articles": {
            "10": {"id": 10, "name": "Bier", "monitor_stock": False},
        }
    }
    validate_stock(ev, [{"article_id": 10, "qty": 99}])


def test_validate_stock_allows_when_enough_stock():
    ev = {
        "articles": {
            "10": {"id": 10, "name": "Bier", "monitor_stock": True, "in_stock": 10},
        }
    }
    validate_stock(ev, [{"article_id": 10, "qty": 3}])
