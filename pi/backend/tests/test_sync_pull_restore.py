"""Manual sync pull restores operational snapshot like background worker."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

from app.cloud_client import ConditionalGetResult
from app.sync_service import pull_and_restore, sync_status


def _write_edge_env(tmp_path: Path, monkeypatch) -> None:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    path.write_text(
        "CLOUD_BASE_URL=https://cloud.test\nEDGE_CLIENT_ID=c1\nEDGE_SECRET=s1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)


def test_pull_and_restore_calls_operational_snapshot(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    sync_status["last_restore_check_at"] = None
    sync_status["snapshot_etag"] = None

    bundle = {"organisation_id": 1, "events": [{"id": 1, "name": "E"}]}
    restore_summary = {"orders": 1}

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, bundle, '"b"')),
    )
    monkeypatch.setattr(
        "app.sync_service.fetch_operational_snapshot",
        AsyncMock(return_value=ConditionalGetResult(False, {"events": []}, '"s"')),
    )
    monkeypatch.setattr("app.sync_service.needs_operational_restore", lambda _db, _snap: True)
    monkeypatch.setattr(
        "app.sync_service.restore_operational_snapshot",
        lambda _db, _snap, _bundle: restore_summary,
    )
    monkeypatch.setattr("app.sync_service.reconcile_bundle_lifecycle", lambda *_a, **_k: [])
    monkeypatch.setattr("app.sync_service.write_ota_freeze_from_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sync_service.reapply_pending_stock", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "app.sync_service.push_outbox",
        AsyncMock(return_value={"sent": 0, "errors": []}),
    )

    result = asyncio.run(pull_and_restore(db, force_restore_check=True))
    assert result["event_count"] == 1
    assert result["restore"] == restore_summary
    assert sync_status["snapshot_etag"] == '"s"'


def test_pull_and_restore_pushes_outbox_before_restore(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    sync_status["last_restore_check_at"] = None
    sync_status["snapshot_etag"] = None
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")
    monkeypatch.setenv("SYNC_PUSH_ENABLED", "1")

    call_order: list[str] = []

    async def fake_push(_db, *, retry_errors=True, client=None):
        call_order.append("push")
        return {"sent": 1, "errors": []}

    def fake_restore(_db, _snap, _bundle):
        call_order.append("restore")
        return {"restored_orders": 1, "purged_ghost_orders": 0}

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, {"organisation_id": 1, "events": [{"id": 1}]}, '"b"')),
    )
    monkeypatch.setattr(
        "app.sync_service.fetch_operational_snapshot",
        AsyncMock(return_value=ConditionalGetResult(False, {"events": [{"event_id": 1, "open_orders": []}]}, '"s"')),
    )
    monkeypatch.setattr("app.sync_service.needs_operational_restore", lambda _db, _snap: True)
    monkeypatch.setattr("app.sync_service.restore_operational_snapshot", fake_restore)
    monkeypatch.setattr("app.sync_service.push_outbox", fake_push)
    monkeypatch.setattr("app.sync_service.reconcile_bundle_lifecycle", lambda *_a, **_k: [])
    monkeypatch.setattr("app.sync_service.write_ota_freeze_from_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sync_service.reapply_pending_stock", lambda *_a, **_k: None)

    result = asyncio.run(pull_and_restore(db, force_restore_check=True))
    assert call_order == ["push", "restore"]
    assert result.get("pre_restore_push", {}).get("sent") == 1
    assert result.get("restore")


def test_pull_and_restore_304_skips_pre_restore_push(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    sync_status["last_restore_check_at"] = None
    sync_status["snapshot_etag"] = '"snap"'
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")

    push_calls: list[int] = []
    restore_calls: list[int] = []

    async def fake_push(*_a, **_k):
        push_calls.append(1)
        return {"sent": 0, "errors": []}

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, {"organisation_id": 1, "events": []}, '"b"')),
    )
    monkeypatch.setattr(
        "app.sync_service.fetch_operational_snapshot",
        AsyncMock(return_value=ConditionalGetResult(True, None, '"snap"')),
    )
    monkeypatch.setattr(
        "app.sync_service.restore_operational_snapshot",
        lambda *_a, **_k: restore_calls.append(1) or {},
    )
    monkeypatch.setattr("app.sync_service.push_outbox", fake_push)
    monkeypatch.setattr("app.sync_service.reconcile_bundle_lifecycle", lambda *_a, **_k: [])
    monkeypatch.setattr("app.sync_service.write_ota_freeze_from_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sync_service.reapply_pending_stock", lambda *_a, **_k: None)

    result = asyncio.run(pull_and_restore(db, force_restore_check=True))
    assert result.get("restore_skipped") == "not_modified"
    assert push_calls == []
    assert restore_calls == []
