"""Smoke tests for edge_api routes not covered elsewhere."""

from unittest.mock import AsyncMock


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_bundle_and_meta_without_pairing(client):
    bundle = client.get("/v1/bundle")
    assert bundle.status_code == 200
    meta = client.get("/v1/meta")
    assert meta.status_code == 200


def test_meta_last_sync_at_serializes_utc_offset(client_session):
    from datetime import datetime

    from app.models import SyncedBundle

    client, Session = client_session
    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.updated_at = datetime(2026, 6, 24, 15, 47, 27)
        db.commit()
    finally:
        db.close()

    meta = client.get("/v1/meta")
    assert meta.status_code == 200
    last_sync_at = meta.json()["last_sync_at"]
    assert last_sync_at is not None
    assert last_sync_at.endswith("+00:00")
    assert "2026-06-24T15:47:27" in last_sync_at

    status = client.get("/v1/sync/status")
    assert status.status_code == 200
    bundle_last_sync_at = status.json()["bundle_last_sync_at"]
    assert bundle_last_sync_at == last_sync_at


def test_sync_status_unconfigured(client, monkeypatch, tmp_path):
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    r = client.get("/v1/sync/status")
    assert r.status_code == 200
    assert r.json()["configured"] is False


def test_cloud_reachable_not_configured(client, monkeypatch, tmp_path):
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    r = client.get("/v1/cloud/reachable")
    assert r.status_code == 200
    assert r.json()["reachable"] is False


def test_admin_status(client):
    r = client.get("/v1/admin/status")
    assert r.status_code == 200


def test_terminal_routes_require_stripe_event(client, bundle):
    b = dict(bundle)
    ev = b["events"][0]
    ev["payment_types"] = ["cash"]
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

    r = client.post("/v1/terminal/connection-token", json={"event_id": ev["id"]})
    assert r.status_code == 403


def test_terminal_connection_token_proxies_cloud(client, bundle, monkeypatch):
    b = dict(bundle)
    ev = b["events"][0]
    ev["payment_types"] = ["stripe_terminal"]
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

    monkeypatch.setattr(
        "app.routers.edge_payments.cloud_create_terminal_connection_token",
        AsyncMock(return_value={"secret": "tok_test"}),
    )
    r = client.post("/v1/terminal/connection-token", json={"event_id": ev["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["secret"] == "tok_test"


def test_payments_list_empty(client, bundle):
    event_id = bundle["events"][0]["id"]
    r = client.get("/v1/payments", params={"event_id": event_id})
    assert r.status_code == 200
    assert isinstance(r.json().get("payments"), list)
