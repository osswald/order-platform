"""Fiscal line snapshots."""

from app.fiscal_vat import split_gross_cents
from app.order_fiscal import snapshot_line


def test_snapshot_line_includes_fiscal_fields():
    articles = {
        "10": {
            "id": 10,
            "name": "Bier",
            "price": 5.0,
            "tax_code_id": 1,
            "tax_rate_percent": 8.1,
            "accounting_account_id": 3,
        }
    }
    line = {"article_id": 10, "qty": 1, "note": "", "additions": []}
    snap = snapshot_line(line, articles, order_number=1)
    assert snap["tax_code_id"] == 1
    assert snap["accounting_account_id"] == 3
    assert snap["gross_cents"] == 500
    assert snap["net_cents"] + snap["vat_cents"] == snap["gross_cents"]


def test_split_gross_cents_rounding():
    gross, net, vat = split_gross_cents(1000, 8.1)
    assert gross == 1000
    assert abs((net + vat) - gross) <= 1
