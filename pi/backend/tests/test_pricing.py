"""Line pricing with article additions."""

from app.order_fiscal import snapshot_line
from app.pricing import line_total_cents, line_unit_cents


def test_snapshotted_line_does_not_double_count_addition_prices():
    arts = {
        "1": {
            "id": 1,
            "name": "Article A",
            "price": 8.0,
            "additions": [{"article_id": 2, "name": "Addon B", "price": 3.0}],
        },
        "2": {"id": 2, "name": "Addon B", "price": 3.0},
    }
    raw = {"article_id": 1, "qty": 1, "additions": [{"article_id": 2, "qty": 1}]}
    assert line_unit_cents(raw, arts) == 1100
    snap = snapshot_line(raw, arts)
    assert snap["unit_cents"] == 1100
    assert snap["additions"][0]["unit_cents"] == 300
    assert line_unit_cents(snap, arts) == 1100
    assert line_total_cents(snap, arts) == 1100
