"""Unit tests for order line merge and selection helpers."""

import pytest
from app.order_line_utils import (
    additions_signature,
    line_key,
    merge_lines_into_list,
    selection_key,
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


def test_selection_key_distinguishes_article_and_voucher():
    art = selection_key({"article_id": 5, "note": "", "qty": 1})
    voucher = selection_key({"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 1})
    assert art != voucher
    assert voucher == selection_key({"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 3, "note": "x"})
    assert voucher != selection_key({"kind": "voucher_sale", "voucher_definition_uuid": "vd-50", "qty": 1})


def test_take_selections_moves_voucher_sale_lines_by_definition_uuid():
    store = {
        1: {
            "lines": [
                {"article_id": 5, "qty": 1, "note": "", "additions": []},
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "voucher_name": "20er",
                    "qty": 3,
                    "note": "",
                    "additions": [],
                    "unit_cents": 2000,
                },
            ]
        }
    }

    class Order:
        id = 1

    moved = take_selections_from_orders(
        [Order()],
        [{"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 2}],
        load_payload=lambda o: store[o.id],
        save_payload=lambda o, p: store.__setitem__(o.id, p),
    )
    assert len(moved) == 1
    assert moved[0]["kind"] == "voucher_sale"
    assert moved[0]["voucher_definition_uuid"] == "vd-20"
    assert moved[0]["voucher_name"] == "20er"
    assert moved[0]["qty"] == 2
    assert moved[0]["unit_cents"] == 2000
    remaining = store[1]["lines"]
    assert {"article_id": 5} == {"article_id": remaining[0]["article_id"]}
    assert remaining[1]["kind"] == "voucher_sale"
    assert remaining[1]["qty"] == 1


def test_take_selections_voucher_over_requested_raises():
    store = {
        1: {
            "lines": [
                {
                    "kind": "voucher_sale",
                    "voucher_definition_uuid": "vd-20",
                    "qty": 1,
                }
            ]
        }
    }

    class Order:
        id = 1

    with pytest.raises(ValueError):
        take_selections_from_orders(
            [Order()],
            [{"kind": "voucher_sale", "voucher_definition_uuid": "vd-20", "qty": 2}],
            load_payload=lambda o: store[o.id],
            save_payload=lambda o, p: store.__setitem__(o.id, p),
        )


def test_merge_lines_combines_voucher_sale_qty_by_definition():
    lines = [
        {"article_id": 1, "qty": 1, "note": ""},
        {
            "kind": "voucher_sale",
            "voucher_definition_uuid": "vd-20",
            "qty": 1,
            "note": "",
            "unit_cents": 2000,
        },
    ]
    merge_lines_into_list(
        lines,
        [
            {
                "kind": "voucher_sale",
                "voucher_definition_uuid": "vd-20",
                "qty": 2,
                "note": "",
                "unit_cents": 2000,
            },
            {
                "kind": "voucher_sale",
                "voucher_definition_uuid": "vd-50",
                "qty": 1,
                "note": "",
                "unit_cents": 5000,
            },
        ],
    )
    assert len(lines) == 3
    assert lines[1]["qty"] == 3
    assert lines[1]["kind"] == "voucher_sale"
    assert lines[2]["voucher_definition_uuid"] == "vd-50"


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
