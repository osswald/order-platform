"""Cloud sync payload helpers."""

from app.domain.sync_enqueue import enrich_payload_for_cloud_sync


def test_enrich_payload_for_cloud_sync_adds_order_ids():
    payload = {"client_order_id": "pwa-abc", "lines": []}
    out = enrich_payload_for_cloud_sync(payload, local_order_id=42, session_id=7)
    assert out["local_order_id"] == 42
    assert out["session_id"] == 7
    assert out["client_order_id"] == "pwa-abc"
