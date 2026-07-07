"""Cloud sync payload helpers."""

from app.domain.sync_enqueue import enrich_payload_for_cloud_sync, event_mode_label


def test_event_mode_label_defaults_missing_status_to_config():
    assert event_mode_label(None) == "config"


def test_event_mode_label_does_not_treat_str_none_as_config():
    assert event_mode_label(str(None)) == "none"


def test_enrich_payload_for_cloud_sync_adds_order_ids():
    payload = {"client_order_id": "pwa-abc", "lines": []}
    out = enrich_payload_for_cloud_sync(payload, local_order_id=42, session_id=7)
    assert out["local_order_id"] == 42
    assert out["session_id"] == 7
    assert out["client_order_id"] == "pwa-abc"


def test_enrich_payload_for_cloud_sync_stamps_mode():
    out = enrich_payload_for_cloud_sync(
        {"client_order_id": "pwa-abc", "lines": []},
        local_order_id=42,
        session_id=7,
        mode="test",
    )
    assert out["mode"] == "test"
