"""SYNC_PUSH_ENABLED=0 skips cloud push."""

import asyncio

from app.sync_service import is_push_enabled, run_sync_cycle


def test_push_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SYNC_PUSH_ENABLED", "0")
    assert is_push_enabled() is False


def test_sync_cycle_skips_push_when_disabled(monkeypatch, tmp_path, isolated_engine, db_session):
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    path.write_text(
        "CLOUD_BASE_URL=https://cloud.test\nEDGE_CLIENT_ID=cid\nEDGE_SECRET=secret\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    monkeypatch.setenv("SYNC_PUSH_ENABLED", "0")
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "0")

    async def _fake_pull(db, **_kwargs):
        return {
            "ok": True,
            "event_count": 0,
            "bundle": {"events": []},
            "purged_event_ids": [],
            "bundle_changed": False,
        }

    monkeypatch.setattr("app.sync_service.pull_bundle", _fake_pull)

    result = asyncio.run(run_sync_cycle(db_session))
    assert result.get("push_skipped") is True
    assert result.get("push_sent", 0) == 0
