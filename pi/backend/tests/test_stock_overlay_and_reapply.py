"""Pending-stock reapply guard and local stock overlay (F+G)."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from app.bundle_cache import get_bundle_dict, get_bundle_dict_raw, invalidate_bundle_cache
from app.cloud_client import ConditionalGetResult
from app.models import LocalStockState, OutboxEntry, SyncedBundle
from app.stock import apply_stock_to_bundle, persist_local_stock, save_bundle
from app.sync_service import pull_and_restore, reapply_pending_stock


def _stock_bundle(*, organisation_id: int = 1, qty: int = 10) -> dict:
    return {
        "organisation_id": organisation_id,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "articles": {
                    "42": {
                        "id": 42,
                        "name": "Beer",
                        "monitor_stock": True,
                        "in_stock": qty,
                        "sellable": qty > 0,
                    }
                },
            }
        ],
    }


def _pending_outbox(db, *, qty: int = 3) -> None:
    db.add(
        OutboxEntry(
            chunk_id=str(uuid.uuid4()),
            entity_type="submission",
            entity_ids_json="[]",
            event_id=1,
            payload_json=json.dumps(
                {
                    "client_order_id": "test-order-1",
                    "event_id": 1,
                    "lines": [{"article_id": 42, "qty": qty}],
                }
            ),
            status="pending",
        )
    )


def test_pull_and_restore_304_does_not_double_decrement(monkeypatch, isolated_engine, db_session):
    db = db_session
    # Local catalogue already reflects pending deduction (effective 7).
    prior = datetime(2026, 1, 1, tzinfo=UTC)
    body = json.dumps(_stock_bundle(qty=7))
    db.add(SyncedBundle(id=1, json_body=body, etag='"e1"', updated_at=prior))
    _pending_outbox(db, qty=3)
    db.commit()
    invalidate_bundle_cache()

    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(True, None, '"e1"')),
    )
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "0")

    result = asyncio.run(pull_and_restore(db, force_restore_check=False))
    assert result["bundle_changed"] is False

    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert row.json_body == body
    assert row.updated_at.replace(tzinfo=UTC) == prior

    effective = get_bundle_dict_raw(db)
    assert effective["events"][0]["articles"]["42"]["in_stock"] == 7


def test_pull_and_restore_identical_body_does_not_reapply(monkeypatch, isolated_engine, db_session):
    db = db_session
    prior = datetime(2026, 1, 1, tzinfo=UTC)
    local = _stock_bundle(qty=7)
    body = json.dumps(local)
    db.add(SyncedBundle(id=1, json_body=body, etag='"old"', updated_at=prior))
    _pending_outbox(db, qty=3)
    db.commit()
    invalidate_bundle_cache()

    cloud = _stock_bundle(qty=7)
    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, cloud, '"new"')),
    )
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "0")

    result = asyncio.run(pull_and_restore(db))
    assert result["bundle_changed"] is False

    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert row.json_body == body
    effective = get_bundle_dict_raw(db)
    assert effective["events"][0]["articles"]["42"]["in_stock"] == 7


def test_pull_and_restore_changed_body_reapplies_pending(monkeypatch, isolated_engine, db_session):
    db = db_session
    # Stale local catalogue; cloud resets stock to 10; pending outbox still owes 3.
    prior = datetime(2026, 1, 1, tzinfo=UTC)
    db.add(
        SyncedBundle(
            id=1,
            json_body=json.dumps(_stock_bundle(qty=7)),
            etag='"old"',
            updated_at=prior,
        )
    )
    _pending_outbox(db, qty=3)
    db.commit()
    invalidate_bundle_cache()

    cloud = _stock_bundle(qty=10)
    monkeypatch.setattr(
        "app.sync_service.fetch_bundle",
        AsyncMock(return_value=ConditionalGetResult(False, cloud, '"new"')),
    )
    monkeypatch.setenv("RESTORE_FROM_CLOUD", "0")

    result = asyncio.run(pull_and_restore(db))
    assert result["bundle_changed"] is True

    effective = get_bundle_dict_raw(db)
    assert effective["events"][0]["articles"]["42"]["in_stock"] == 7

    # Catalogue baseline is cloud (10); overlay holds local absolute (7).
    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    catalogue = json.loads(row.json_body)
    assert catalogue["events"][0]["articles"]["42"]["in_stock"] == 10
    overlay = (
        db.query(LocalStockState)
        .filter(
            LocalStockState.event_id == 1,
            LocalStockState.entity_kind == "article",
            LocalStockState.entity_id == 42,
        )
        .first()
    )
    assert overlay is not None
    assert float(overlay.in_stock) == 7.0


def test_persist_local_stock_does_not_rewrite_catalogue(isolated_engine, db_session):
    db = db_session
    prior = datetime(2026, 1, 1, tzinfo=UTC)
    catalogue = _stock_bundle(qty=10)
    body = json.dumps(catalogue)
    db.add(SyncedBundle(id=1, json_body=body, updated_at=prior))
    db.commit()
    invalidate_bundle_cache()

    bundle = get_bundle_dict(db)
    apply_stock_to_bundle(bundle, 1, [{"article_id": 42, "qty": 3}], strict=True)
    persist_local_stock(db, bundle, event_ids={1})
    db.commit()

    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    assert row.json_body == body
    assert row.updated_at.replace(tzinfo=UTC) == prior

    warm = get_bundle_dict(db)
    assert warm["events"][0]["articles"]["42"]["in_stock"] == 7

    invalidate_bundle_cache()
    cold = get_bundle_dict(db)
    assert cold["events"][0]["articles"]["42"]["in_stock"] == 7


def test_save_bundle_stock_path_uses_overlay(isolated_engine, db_session):
    db = db_session
    body = json.dumps(_stock_bundle(qty=5))
    db.add(SyncedBundle(id=1, json_body=body))
    db.commit()
    invalidate_bundle_cache()

    bundle = get_bundle_dict(db)
    apply_stock_to_bundle(bundle, 1, [{"article_id": 42, "qty": 2}])
    save_bundle(db, bundle)
    db.commit()

    assert json.loads(db.query(SyncedBundle).one().json_body)["events"][0]["articles"]["42"]["in_stock"] == 5
    assert get_bundle_dict(db)["events"][0]["articles"]["42"]["in_stock"] == 3


def test_reapply_pending_stock_writes_overlay_not_catalogue(isolated_engine, db_session):
    db = db_session
    cloud = _stock_bundle(qty=10)
    body = json.dumps(cloud)
    db.add(SyncedBundle(id=1, json_body=body))
    _pending_outbox(db, qty=3)
    db.commit()

    data = json.loads(json.dumps(cloud))
    reapply_pending_stock(db, data)
    db.commit()

    row = db.query(SyncedBundle).one()
    assert row.json_body == body
    assert data["events"][0]["articles"]["42"]["in_stock"] == 7
    assert get_bundle_dict_raw(db)["events"][0]["articles"]["42"]["in_stock"] == 7


def test_alembic_head_is_local_stock_overlay():
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    assert head == "009_local_stock_overlay"
