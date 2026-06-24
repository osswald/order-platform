"""Outbox push transaction boundaries."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.cloud_client import CloudConfigError
from app.models import OutboxEntry
from app.sync_service import push_outbox


def _add_outbox_rows(db, specs):
    for spec in specs:
        db.add(
            OutboxEntry(
                chunk_id=spec["chunk_id"],
                event_id=1,
                entity_type=spec.get("entity_type", "order"),
                payload_json=json.dumps(spec.get("payload", {"client_order_id": spec["chunk_id"], "lines": []})),
                status=spec.get("status", "pending"),
                attempt_count=spec.get("attempt_count", 0),
            )
        )
    db.commit()


def test_push_outbox_commits_once_after_batch(db_session, monkeypatch):
    db = db_session
    _add_outbox_rows(
        db,
        [{"chunk_id": f"chunk-{i}"} for i in range(3)],
    )

    commits: list[int] = []
    original_commit = db.commit

    def track_commit():
        commits.append(1)
        return original_commit()

    monkeypatch.setattr(db, "commit", track_commit)
    monkeypatch.setattr(
        "app.sync_service.submit_operational_chunk",
        AsyncMock(return_value=None),
    )

    result = asyncio.run(push_outbox(db, retry_errors=False))
    assert result["sent"] == 3
    assert len(commits) == 1

    rows = db.query(OutboxEntry).order_by(OutboxEntry.id.asc()).all()
    assert all(row.status == "acked" for row in rows)


def test_push_outbox_partial_failure_mixed_statuses(db_session, monkeypatch):
    db = db_session
    _add_outbox_rows(
        db,
        [
            {"chunk_id": "chunk-ok-1"},
            {"chunk_id": "chunk-fail"},
            {"chunk_id": "chunk-ok-2"},
        ],
    )

    async def submit_side_effect(*, chunk_id, **kwargs):
        if chunk_id == "chunk-fail":
            raise RuntimeError("cloud rejected")

    monkeypatch.setattr(
        "app.sync_service.submit_operational_chunk",
        AsyncMock(side_effect=submit_side_effect),
    )

    commits: list[int] = []
    original_commit = db.commit

    def track_commit():
        commits.append(1)
        return original_commit()

    monkeypatch.setattr(db, "commit", track_commit)

    result = asyncio.run(push_outbox(db, retry_errors=False))
    assert result["sent"] == 2
    assert len(result["errors"]) == 1
    assert len(commits) == 1

    rows = {row.chunk_id: row for row in db.query(OutboxEntry).all()}
    assert rows["chunk-ok-1"].status == "acked"
    assert rows["chunk-ok-2"].status == "acked"
    assert rows["chunk-fail"].status == "error"
    assert rows["chunk-fail"].attempt_count == 1


def test_push_outbox_cloud_config_error_does_not_commit(db_session, monkeypatch):
    db = db_session
    _add_outbox_rows(db, [{"chunk_id": "chunk-1"}, {"chunk_id": "chunk-2"}])

    async def submit_side_effect(*, chunk_id, **kwargs):
        if chunk_id == "chunk-2":
            raise CloudConfigError("missing credentials")

    monkeypatch.setattr(
        "app.sync_service.submit_operational_chunk",
        AsyncMock(side_effect=submit_side_effect),
    )

    commits: list[int] = []
    original_commit = db.commit

    def track_commit():
        commits.append(1)
        return original_commit()

    monkeypatch.setattr(db, "commit", track_commit)

    with pytest.raises(CloudConfigError):
        asyncio.run(push_outbox(db, retry_errors=False))

    assert commits == []
    rows = {row.chunk_id: row for row in db.query(OutboxEntry).all()}
    assert rows["chunk-1"].status == "acked"
    assert rows["chunk-2"].status == "pending"


def test_push_outbox_retry_errors_includes_error_rows(db_session, monkeypatch):
    db = db_session
    _add_outbox_rows(
        db,
        [
            {"chunk_id": "chunk-error", "status": "error", "attempt_count": 2},
            {"chunk_id": "chunk-pending", "status": "pending"},
        ],
    )

    monkeypatch.setattr(
        "app.sync_service.submit_operational_chunk",
        AsyncMock(return_value=None),
    )

    result = asyncio.run(push_outbox(db, retry_errors=True))
    assert result["sent"] == 2
    rows = {row.chunk_id: row for row in db.query(OutboxEntry).all()}
    assert rows["chunk-error"].status == "acked"
    assert rows["chunk-pending"].status == "acked"
