"""Pi edge proxy for SumUp Cloud checkouts."""

from unittest.mock import AsyncMock


def _patch_bundle_payment_types(bundle: dict, payment_types: list[str]) -> None:
    b = dict(bundle)
    ev = dict(b["events"][0])
    ev["payment_types"] = payment_types
    b["events"] = [ev]
    import json

    from app.database import SessionLocal
    from app.models import SyncedBundle

    db = SessionLocal()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(b)
        db.commit()
    finally:
        db.close()


def test_sumup_routes_require_sumup_connected_event(client, bundle):
    _patch_bundle_payment_types(bundle, ["cash"])
    ev = bundle["events"][0]
    r = client.post(
        "/v1/sumup/checkout",
        json={
            "event_id": ev["id"],
            "amount_cents": 500,
            "currency": "CHF",
            "reader_id": "rdr_test",
        },
    )
    assert r.status_code == 403


def test_sumup_checkout_proxies_cloud(client, bundle, monkeypatch):
    _patch_bundle_payment_types(bundle, ["sumup_connected"])
    ev = bundle["events"][0]
    monkeypatch.setattr(
        "app.routers.edge_sumup.cloud_create_sumup_checkout",
        AsyncMock(
            return_value={
                "checkout_id": "co_test",
                "status": "pending",
            }
        ),
    )
    r = client.post(
        "/v1/sumup/checkout",
        json={
            "event_id": ev["id"],
            "amount_cents": 500,
            "currency": "CHF",
            "reader_id": "rdr_test",
            "client_order_id": "order-1",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["checkout_id"] == "co_test"


def test_sumup_status_proxies_cloud(client, bundle, monkeypatch):
    _patch_bundle_payment_types(bundle, ["sumup_connected"])
    ev = bundle["events"][0]
    monkeypatch.setattr(
        "app.routers.edge_sumup.cloud_get_sumup_checkout_status",
        AsyncMock(
            return_value={
                "checkout_id": "co_test",
                "status": "paid",
                "transaction_id": "txn_1",
                "receipt_info": {
                    "card_type": "VISA",
                    "card_last_4": "1111",
                    "auth_code": "99",
                    "transaction_code": "CODE99",
                    "entry_mode": "CHIP",
                },
            }
        ),
    )
    r = client.get(
        "/v1/sumup/status",
        params={"event_id": ev["id"], "checkout_id": "co_test"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["transaction_id"] == "txn_1"
    assert body["receipt_info"]["card_last_4"] == "1111"
