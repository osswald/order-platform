"""Hosted-Pi /v1/ops/purge-operational endpoint."""

from __future__ import annotations

import json

import pytest
from app.models import EmulatedReceipt, LocalOrder, SyncedBundle
from app.models_operational import OrderSession


@pytest.fixture
def hosted_cleanup(monkeypatch, api_context):
    monkeypatch.setenv("HOSTED_PI", "1")
    monkeypatch.setenv("PLAY_REVIEW_CLEANUP_SECRET", "test-cleanup-secret")
    return api_context


def _seed_bundle_and_orders(Session, *, event_id: int = 1, status: str = "test"):
    db = Session()
    try:
        bundle = {
            "organisation_id": 1,
            "appliance_id": 1,
            "events": [{"id": event_id, "status": status, "name": "Demo"}],
        }
        db.merge(SyncedBundle(id=1, json_body=json.dumps(bundle)))
        db.add(OrderSession(event_id=event_id, table_number=1, order_source="waiter", status="OPEN"))
        db.flush()
        session_id = db.query(OrderSession).first().id
        db.add(
            LocalOrder(
                session_id=session_id,
                client_order_id="o-demo",
                event_id=event_id,
                table_number=1,
                payment_status="open",
                payload_json="{}",
            )
        )
        db.add(
            EmulatedReceipt(
                job_kind="receipt",
                station_name="Bar",
                escpos_payload="e30=",
                preview_text="demo",
            )
        )
        db.commit()
    finally:
        db.close()


def test_purge_operational_requires_hosted_and_secret(client, monkeypatch):
    monkeypatch.delenv("HOSTED_PI", raising=False)
    monkeypatch.delenv("PLAY_REVIEW_CLEANUP_SECRET", raising=False)
    assert client.post("/v1/ops/purge-operational").status_code == 404

    monkeypatch.setenv("HOSTED_PI", "1")
    monkeypatch.setenv("PLAY_REVIEW_CLEANUP_SECRET", "secret")
    assert client.post("/v1/ops/purge-operational").status_code == 401
    assert (
        client.post(
            "/v1/ops/purge-operational",
            headers={"X-Cleanup-Secret": "wrong"},
        ).status_code
        == 401
    )


def test_purge_operational_clears_orders_and_receipts_keeps_status(hosted_cleanup):
    client = hosted_cleanup.client
    Session = hosted_cleanup.Session
    _seed_bundle_and_orders(Session, event_id=1, status="test")

    res = client.post(
        "/v1/ops/purge-operational",
        headers={"X-Cleanup-Secret": "test-cleanup-secret"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["purged_event_ids"] == [1]

    db = Session()
    try:
        assert db.query(LocalOrder).count() == 0
        assert db.query(EmulatedReceipt).count() == 0
        bundle = json.loads(db.query(SyncedBundle).filter(SyncedBundle.id == 1).one().json_body)
        assert bundle["events"][0]["status"] == "test"
    finally:
        db.close()
