"""SYNC_PUSH_ENABLED=0 skips cloud push."""

import asyncio

from app.sync_service import is_push_enabled, run_sync_cycle


def test_push_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SYNC_PUSH_ENABLED", "0")
    assert is_push_enabled() is False


def test_sync_cycle_skips_push_when_disabled(monkeypatch):
    monkeypatch.setenv("SYNC_PUSH_ENABLED", "0")
    monkeypatch.setenv("CLOUD_BASE_URL", "https://cloud.test")
    monkeypatch.setenv("EDGE_CLIENT_ID", "cid")
    monkeypatch.setenv("EDGE_SECRET", "secret")

    async def _fake_pull(db):
        return {"ok": True, "event_count": 0, "bundle": {"events": []}, "purged_event_ids": []}

    monkeypatch.setattr("app.sync_service.pull_bundle", _fake_pull)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        result = asyncio.run(run_sync_cycle(db))
    finally:
        db.close()
    assert result.get("push_skipped") is True
    assert result.get("push_sent", 0) == 0
