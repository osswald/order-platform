"""Sync service configuration and cycle."""

import asyncio
import json
from pathlib import Path

from app.models import OutboxEntry, SyncedBundle
from app.sync_service import is_cloud_configured, pending_outbox_count, run_sync_cycle


def _write_edge_env(tmp_path: Path, monkeypatch) -> None:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    path.write_text(
        "CLOUD_BASE_URL=https://cloud.test\nEDGE_CLIENT_ID=c1\nEDGE_SECRET=s1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)


def test_is_cloud_configured_false_without_env(monkeypatch, tmp_path):
    import app.edge_config as edge_config

    path = tmp_path / "empty.env"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    assert is_cloud_configured() is False


def test_pending_outbox_count(isolated_engine, db_session):
    db = db_session
    db.add(
        OutboxEntry(
            chunk_id="c1",
            event_id=1,
            entity_type="order",
            payload_json=json.dumps({"lines": []}),
            status="pending",
        )
    )
    db.commit()
    assert pending_outbox_count(db) == 1


def test_run_sync_cycle_pull_and_push(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session

    async def fake_fetch_bundle():
        return {"organisation_id": 1, "events": [{"id": 1, "name": "E"}]}

    async def fake_push(db, *, retry_errors=True):
        return {"sent": 0, "errors": []}

    monkeypatch.setattr("app.sync_service.fetch_bundle", fake_fetch_bundle)
    monkeypatch.setattr("app.sync_service.push_outbox", fake_push)

    summary = asyncio.run(run_sync_cycle(db))
    assert summary["skipped"] is False
    assert summary["pull_ok"] is True
    assert summary["event_count"] == 1
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert row is not None
    assert json.loads(row.json_body)["organisation_id"] == 1
