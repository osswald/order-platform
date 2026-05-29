"""Addition label resolution for slips and snapshots."""

from app.order_fiscal import _snapshot_additions
from app.pricing import addition_display_name
from app.print_worker import build_escpos_receipt_text, _escpos_text


def test_addition_display_name_prefers_bundle_label():
    arts = {
        "10": {
            "id": 10,
            "name": "Schnitzel Internal",
            "price": 9.5,
            "additions": [
                {
                    "article_id": 30,
                    "name": "Ketchup Internal",
                    "label": "Ketchup",
                    "price": 0.5,
                }
            ],
        },
        "30": {"id": 30, "name": "Ketchup Internal", "label": "Ketchup", "price": 0.5},
    }
    base = arts["10"]
    assert addition_display_name({"article_id": 30, "qty": 1}, arts, base) == "Ketchup"


def test_snapshot_additions_stores_label():
    arts = {
        "10": {
            "id": 10,
            "name": "Burger",
            "additions": [{"article_id": 20, "name": "X", "label": "XL", "price": 1}],
        },
        "20": {"id": 20, "name": "X", "label": "XL", "price": 1},
    }
    snap = _snapshot_additions([{"article_id": 20, "qty": 1}], arts, arts["10"])
    assert snap[0]["name"] == "XL"


def test_slip_prints_addition_label():
    arts = {
        "10": {
            "id": 10,
            "name": "Schnitzel",
            "price": 9.5,
            "additions": [{"article_id": 30, "name": "Int", "label": "Ketchup", "price": 0.5}],
        },
        "30": {"id": 30, "name": "Int", "label": "Ketchup", "price": 0.5},
    }
    slip = build_escpos_receipt_text(
        {
            "table_number": 1,
            "ordered_at": "2024-01-22T10:07:00+00:00",
            "lines": [
                {
                    "article_id": 10,
                    "qty": 1,
                    "additions": [{"article_id": 30, "qty": 1}],
                }
            ],
        },
        "Event",
        articles=arts,
    )
    assert _escpos_text("Ketchup") in slip
    assert _escpos_text("Zusatz #30") not in slip
    assert _escpos_text("+ Ketchup") in slip
    assert _escpos_text("0.50") not in slip
