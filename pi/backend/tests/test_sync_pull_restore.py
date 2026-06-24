"""Manual sync pull restores operational snapshot like background worker."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

from app.sync_service import pull_and_restore


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

    bundle = {"organisation_id": 1, "events": [{"id": 1, "name": "E"}]}
    restore_summary = {"orders": 1}

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=bundle),
    )
    monkeypatch.setattr(
        "app.sync_service.fetch_operational_snapshot",
        AsyncMock(return_value={"events": []}),
    )
    monkeypatch.setattr("app.sync_service.needs_operational_restore", lambda _db, _snap: True)
    monkeypatch.setattr(
        "app.sync_service.restore_operational_snapshot",
        lambda _db, _snap, _bundle: restore_summary,
    )

    result = asyncio.run(pull_and_restore(db))
    assert result["event_count"] == 1
    assert result["restore"] == restore_summary
