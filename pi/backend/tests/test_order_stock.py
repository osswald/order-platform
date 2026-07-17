"""Order stock validation endpoint and create-order stock guards."""

import json

from app.models import SyncedBundle
from tests.fixtures_bundles import bundle_copy, default_bundle


def _seed_stock_bundle(Session, *, in_stock: int = 2) -> None:
    bundle = bundle_copy(default_bundle())
    ev = bundle["events"][0]
    ev["articles"] = {
        "10": {
            "id": 10,
            "name": "Bier",
            "price": 5.0,
            "additions": [],
            "monitor_stock": True,
            "in_stock": in_stock,
            "sellable": in_stock > 0,
        }
    }
    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(bundle)
        db.commit()
    finally:
        db.close()


def test_validate_order_stock_ok(client_session):
    client, Session = client_session
    _seed_stock_bundle(Session, in_stock=5)
    res = client.post(
        "/v1/stock/validate-order",
        json={
            "event_id": 1,
            "lines": [{"article_id": 10, "qty": 3, "additions": []}],
        },
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"ok": True}


def test_validate_order_stock_insufficient(client_session):
    client, Session = client_session
    _seed_stock_bundle(Session, in_stock=2)
    res = client.post(
        "/v1/stock/validate-order",
        json={
            "event_id": 1,
            "lines": [{"article_id": 10, "qty": 5, "additions": []}],
        },
    )
    assert res.status_code == 409, res.text
    detail = res.json()["detail"]
    assert detail["code"] == "stock_insufficient"
    assert detail["issues"]


def test_create_order_insufficient_stock_no_order_no_deduct(client_session):
    from app.models import LocalOrder

    client, Session = client_session
    _seed_stock_bundle(Session, in_stock=2)
    res = client.post(
        "/v1/orders",
        json={
            "client_order_id": "stock-fail-001",
            "event_id": 1,
            "table_number": 5,
            "order_source": "waiter",
            "lines": [{"article_id": 10, "qty": 5, "note": ""}],
        },
    )
    assert res.status_code == 409, res.text

    db = Session()
    try:
        assert db.query(LocalOrder).filter(LocalOrder.client_order_id == "stock-fail-001").first() is None
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        bundle = json.loads(row.json_body)
        assert bundle["events"][0]["articles"]["10"]["in_stock"] == 2
    finally:
        db.close()
