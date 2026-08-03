"""Shared HTTP client, conditional bundle pull, and restore-check debounce."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
from app.cloud_client import ConditionalGetResult
from app.models import OutboxEntry, SyncedBundle
from app.sync_service import (
    pull_and_restore,
    pull_bundle,
    push_outbox,
    run_sync_cycle,
    should_check_operational_restore,
    sync_status,
)


def _write_edge_env(tmp_path: Path, monkeypatch) -> None:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    path.write_text(
        "CLOUD_BASE_URL=https://cloud.test\nEDGE_CLIENT_ID=c1\nEDGE_SECRET=s1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)


def _bundle_payload(**overrides) -> dict:
    data = {
        "organisation_id": 1,
        "server_time": "2026-08-03T12:00:00+00:00",
        "events": [{"id": 1, "name": "E"}],
    }
    data.update(overrides)
    return data


def test_run_sync_cycle_reuses_one_http_client(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    for i in range(2):
        db.add(
            OutboxEntry(
                chunk_id=f"chunk-{i}",
                event_id=1,
                entity_type="order",
                payload_json=json.dumps({"client_order_id": f"chunk-{i}", "lines": []}),
                status="pending",
            )
        )
    db.commit()

    clients_seen: list[object] = []

    class TrackingClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            clients_seen.append(self)

        async def get(self, url, headers=None, params=None):
            request = httpx.Request("GET", str(url))
            if "operational/snapshot" in str(url):
                return httpx.Response(
                    200,
                    request=request,
                    json={"fingerprint": "fp", "events": []},
                    headers={"ETag": '"snap1"'},
                )
            return httpx.Response(
                200,
                request=request,
                json=_bundle_payload(),
                headers={"ETag": '"b1"'},
            )

        async def post(self, url, headers=None, json=None):
            request = httpx.Request("POST", str(url))
            return httpx.Response(200, request=request, json={"ok": True})

    monkeypatch.setattr("app.cloud_client.httpx.AsyncClient", TrackingClient)
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "0")
    monkeypatch.setenv("SYNC_PUSH_ENABLED", "1")

    summary = asyncio.run(run_sync_cycle(db))
    assert summary["pull_ok"] is True
    assert summary["push_sent"] == 2
    assert len(clients_seen) == 1


def test_pull_bundle_304_skips_rewrite_and_logo_clear(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    body = json.dumps(_bundle_payload())
    prior = datetime(2026, 1, 1, tzinfo=UTC)
    db.add(SyncedBundle(id=1, json_body=body, etag='"etag-1"', updated_at=prior))
    db.commit()

    clears: list[int] = []
    monkeypatch.setattr(
        "app.sync_service.clear_receipt_logo_cache",
        lambda: clears.append(1),
    )
    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(True, None, '"etag-1"')),
    )

    result = asyncio.run(pull_bundle(db))
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert result["bundle_changed"] is False
    assert row.updated_at.replace(tzinfo=UTC) == prior
    assert row.json_body == body
    assert clears == []


def test_pull_bundle_200_new_body_writes_and_clears_logo(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    db.add(
        SyncedBundle(
            id=1,
            json_body=json.dumps(_bundle_payload(events=[{"id": 1, "name": "Old"}])),
            etag='"old"',
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    db.commit()

    clears: list[int] = []
    monkeypatch.setattr(
        "app.sync_service.clear_receipt_logo_cache",
        lambda: clears.append(1),
    )
    new_bundle = _bundle_payload(events=[{"id": 1, "name": "New"}])
    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, new_bundle, '"new"')),
    )
    monkeypatch.setattr("app.sync_service.reconcile_bundle_lifecycle", lambda *_a, **_k: [])
    monkeypatch.setattr("app.sync_service.write_ota_freeze_from_bundle", lambda *_a, **_k: None)

    result = asyncio.run(pull_bundle(db))
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert result["bundle_changed"] is True
    assert row.etag == '"new"'
    assert json.loads(row.json_body)["events"][0]["name"] == "New"
    assert clears == [1]


def test_pull_bundle_no_etag_identical_body_skips_rewrite(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    stored = _bundle_payload(server_time="2026-01-01T00:00:00+00:00")
    prior = datetime(2026, 1, 1, tzinfo=UTC)
    db.add(SyncedBundle(id=1, json_body=json.dumps(stored), etag=None, updated_at=prior))
    db.commit()

    clears: list[int] = []
    monkeypatch.setattr(
        "app.sync_service.clear_receipt_logo_cache",
        lambda: clears.append(1),
    )
    # Same content, different server_time, no ETag — must skip rewrite via content hash.
    downloaded = _bundle_payload(server_time="2026-08-03T18:00:00+00:00")
    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, downloaded, None)),
    )

    result = asyncio.run(pull_bundle(db))
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert result["bundle_changed"] is False
    assert row.updated_at.replace(tzinfo=UTC) == prior
    assert clears == []


def test_snapshot_304_skips_restore_but_records_check(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    sync_status["snapshot_etag"] = '"snap-old"'
    sync_status["last_restore_check_at"] = None

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, _bundle_payload(), '"b"')),
    )
    monkeypatch.setattr("app.sync_service.reconcile_bundle_lifecycle", lambda *_a, **_k: [])
    monkeypatch.setattr("app.sync_service.write_ota_freeze_from_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sync_service.reapply_pending_stock", lambda *_a, **_k: None)
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")

    restore_calls: list[int] = []
    monkeypatch.setattr(
        "app.sync_service.fetch_operational_snapshot",
        AsyncMock(return_value=ConditionalGetResult(True, None, '"snap-old"')),
    )
    monkeypatch.setattr(
        "app.sync_service.restore_operational_snapshot",
        lambda *_a, **_k: restore_calls.append(1) or {},
    )

    result = asyncio.run(pull_and_restore(db, force_restore_check=True))
    assert restore_calls == []
    assert result.get("restore_skipped") == "not_modified"
    assert sync_status["last_restore_check_at"] is not None


def test_should_check_operational_restore_idle_skip(monkeypatch, isolated_engine, db_session):
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")
    monkeypatch.setenv("SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS", "300")
    sync_status["last_restore_check_at"] = datetime.now(UTC).isoformat()
    assert (
        should_check_operational_restore(
            db_session,
            bundle_changed=False,
            force=False,
        )
        is False
    )


def test_should_check_operational_restore_forces(monkeypatch, isolated_engine, db_session):
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")
    monkeypatch.setenv("SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS", "300")
    sync_status["last_restore_check_at"] = datetime.now(UTC).isoformat()

    assert should_check_operational_restore(db_session, bundle_changed=True, force=False) is True
    assert should_check_operational_restore(db_session, bundle_changed=False, force=True) is True

    db_session.add(
        OutboxEntry(
            chunk_id="pending-1",
            event_id=1,
            entity_type="order",
            payload_json="{}",
            status="pending",
        )
    )
    db_session.commit()
    assert should_check_operational_restore(db_session, bundle_changed=False, force=False) is True


def test_should_check_operational_restore_max_idle(monkeypatch, isolated_engine, db_session):
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")
    monkeypatch.setenv("SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS", "60")
    sync_status["last_restore_check_at"] = (datetime.now(UTC) - timedelta(seconds=120)).isoformat()
    assert should_check_operational_restore(db_session, bundle_changed=False, force=False) is True


def test_pull_and_restore_skips_snapshot_when_debounced(monkeypatch, tmp_path, isolated_engine, db_session):
    _write_edge_env(tmp_path, monkeypatch)
    db = db_session
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "1")
    monkeypatch.setenv("SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS", "300")
    sync_status["last_restore_check_at"] = datetime.now(UTC).isoformat()

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(True, None, '"e"')),
    )
    db.add(
        SyncedBundle(
            id=1,
            json_body=json.dumps(_bundle_payload()),
            etag='"e"',
            updated_at=datetime.now(UTC),
        )
    )
    db.commit()

    snap = AsyncMock(side_effect=AssertionError("snapshot should not be called"))
    monkeypatch.setattr("app.sync_service.fetch_operational_snapshot", snap)

    result = asyncio.run(pull_and_restore(db, force_restore_check=False))
    assert result["bundle_changed"] is False
    snap.assert_not_called()


def test_content_fingerprint_ignores_server_time():
    from app.sync_service import bundle_content_fingerprint

    a = _bundle_payload(server_time="t1")
    b = _bundle_payload(server_time="t2")
    assert bundle_content_fingerprint(a) == bundle_content_fingerprint(b)
    assert len(bundle_content_fingerprint(a)) == 64
    # sanity: real sha256
    body = {k: v for k, v in a.items() if k != "server_time"}
    expected = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    assert bundle_content_fingerprint(a) == expected


def test_push_outbox_passes_shared_client(monkeypatch, isolated_engine, db_session):
    db = db_session
    db.add(
        OutboxEntry(
            chunk_id="c1",
            event_id=1,
            entity_type="order",
            payload_json=json.dumps({"client_order_id": "c1", "lines": []}),
            status="pending",
        )
    )
    db.commit()

    seen: list[object] = []
    client = object()

    async def fake_submit(**kwargs):
        seen.append(kwargs.get("client"))
        return {}

    monkeypatch.setattr("app.sync_service.submit_operational_chunk", fake_submit)
    asyncio.run(push_outbox(db, client=client))
    assert seen == [client]
