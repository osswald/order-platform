"""Unit tests for order line merge and selection helpers."""

import pytest

from app.order_line_utils import (
    additions_signature,
    line_key,
    merge_lines_into_list,
    normalize_additions,
    take_selections_from_orders,
)


def test_line_key_and_additions_signature():
    key = line_key(10, "note", [{"article_id": 1, "qty": 2}], None)
    assert key[0] == 10
    assert key[1] == "note"
    assert additions_signature([{"article_id": 1, "qty": 2}]) == key[2]


def test_merge_lines_into_list_combines_qty():
    lines = [{"article_id": 1, "qty": 1, "note": ""}]
    merge_lines_into_list(lines, [{"article_id": 1, "qty": 2, "note": ""}])
    assert lines[0]["qty"] == 3


def test_take_selections_from_orders():
    store = {
        1: {
            "lines": [
                {"article_id": 5, "qty": 3, "note": "", "additions": []},
            ]
        }
    }

    class Order:
        def __init__(self, oid):
            self.id = oid

    def load_payload(order):
        return store[order.id]

    def save_payload(order, payload):
        store[order.id] = payload

    moved = take_selections_from_orders(
        [Order(1)],
        [{"article_id": 5, "qty": 2, "note": ""}],
        load_payload=load_payload,
        save_payload=save_payload,
    )
    assert len(moved) == 1
    assert moved[0]["qty"] == 2
    assert store[1]["lines"][0]["qty"] == 1


def test_take_selections_raises_when_over_requested():
    store = {1: {"lines": [{"article_id": 1, "qty": 1, "note": ""}]}}

    class Order:
        id = 1

    with pytest.raises(ValueError):
        take_selections_from_orders(
            [Order()],
            [{"article_id": 1, "qty": 5}],
            load_payload=lambda o: store[o.id],
            save_payload=lambda o, p: store.__setitem__(o.id, p),
        )
