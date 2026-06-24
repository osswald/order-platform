"""Outbox push transaction boundaries."""

import asyncio
import json
from unittest.mock import AsyncMock

from app.models import OutboxEntry
from app.sync_service import push_outbox


def test_push_outbox_commits_once_after_batch(db_session, monkeypatch):
    db = db_session
    for i in range(3):
        db.add(
            OutboxEntry(
                chunk_id=f"chunk-{i}",
                event_id=1,
                entity_type="order",
                payload_json=json.dumps({"client_order_id": f"o-{i}", "lines": []}),
                status="pending",
            )
        )
    db.commit()

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
