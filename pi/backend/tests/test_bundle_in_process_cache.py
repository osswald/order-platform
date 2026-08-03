"""In-process organisation bundle cache."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest
from app.bundle_cache import (
    get_bundle_dict,
    get_bundle_dict_raw,
    invalidate_bundle_cache,
    set_bundle_cache,
)
from app.cloud_client import ConditionalGetResult
from app.models import SyncedBundle
from app.stock import save_bundle
from fastapi import HTTPException
from tests.fixtures_bundles import default_bundle


@pytest.fixture(autouse=True)
def _clear_bundle_cache():
    invalidate_bundle_cache()
    yield
    invalidate_bundle_cache()


def _seed(db, bundle: dict | None = None, *, etag: str | None = None) -> dict:
    data = bundle if bundle is not None else default_bundle()
    db.add(SyncedBundle(id=1, json_body=json.dumps(data), etag=etag))
    db.commit()
    return data


def test_cold_miss_loads_once_then_warm_skips_json_loads(isolated_engine, db_session):
    db = db_session
    _seed(db)
    loads: list[str] = []
    real_loads = json.loads

    def tracking_loads(s, *args, **kwargs):
        loads.append(s if isinstance(s, str) else str(s))
        return real_loads(s, *args, **kwargs)

    with patch("app.bundle_cache.json.loads", side_effect=tracking_loads):
        first = get_bundle_dict(db)
        second = get_bundle_dict(db)

    assert first["organisation_id"] == 1
    assert second["organisation_id"] == 1
    assert len(loads) == 1


def test_warm_raw_read_also_skips_parse(isolated_engine, db_session):
    db = db_session
    _seed(db)
    get_bundle_dict(db)
    loads: list[int] = []
    real_loads = json.loads

    def tracking_loads(s, *args, **kwargs):
        loads.append(1)
        return real_loads(s, *args, **kwargs)

    with patch("app.bundle_cache.json.loads", side_effect=tracking_loads):
        raw = get_bundle_dict_raw(db)

    assert raw is not None
    assert raw["organisation_id"] == 1
    assert loads == []


def test_save_bundle_updates_cache_for_next_read(isolated_engine, db_session):
    db = db_session
    _seed(db)
    warm = get_bundle_dict(db)
    assert warm["events"][0]["articles"]["10"]["name"] == "Bier"

    mutated = get_bundle_dict(db)
    mutated["events"][0]["articles"]["10"]["name"] = "Bier XL"
    mutated["events"][0]["articles"]["10"]["sellable"] = 3
    save_bundle(db, mutated)
    db.commit()

    # Corrupt durable body would still be ignored if cache were stale-wrong;
    # ensure cache reflects save_bundle mutation without another mistaken old parse.
    next_read = get_bundle_dict(db)
    assert next_read["events"][0]["articles"]["10"]["name"] == "Bier XL"
    assert next_read["events"][0]["articles"]["10"]["sellable"] == 3


def test_invalidate_forces_reload_from_sqlite(isolated_engine, db_session):
    db = db_session
    _seed(db)
    get_bundle_dict(db)

    row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
    updated = default_bundle()
    updated["events"][0]["name"] = "Reloaded"
    row.json_body = json.dumps(updated)
    db.commit()

    # Without invalidate, warm cache would still show "Test"
    assert get_bundle_dict(db)["events"][0]["name"] == "Test"
    invalidate_bundle_cache()
    assert get_bundle_dict(db)["events"][0]["name"] == "Reloaded"


def test_get_bundle_dict_raises_when_unpaired(isolated_engine, db_session):
    db = db_session
    with pytest.raises(HTTPException) as exc:
        get_bundle_dict(db)
    assert exc.value.status_code == 400


def test_get_bundle_dict_raw_returns_none_when_empty(isolated_engine, db_session):
    assert get_bundle_dict_raw(db_session) is None


def test_read_returns_isolated_copy(isolated_engine, db_session):
    db = db_session
    _seed(db)
    a = get_bundle_dict(db)
    a["events"][0]["name"] = "MutatedInCaller"
    b = get_bundle_dict(db)
    assert b["events"][0]["name"] == "Test"


def test_pull_bundle_304_leaves_warm_cache(monkeypatch, isolated_engine, db_session):
    from app.sync_service import pull_bundle

    db = db_session
    data = _seed(db, etag='"e1"')
    set_bundle_cache(data)

    loads: list[int] = []
    real_loads = json.loads

    def tracking_loads(s, *args, **kwargs):
        loads.append(1)
        return real_loads(s, *args, **kwargs)

    async def fake_fetch(*, client=None, etag=None):
        return ConditionalGetResult(True, None, '"e1"')

    monkeypatch.setattr("app.sync_service.fetch_bundle", fake_fetch)

    with patch("app.bundle_cache.json.loads", side_effect=tracking_loads):
        result = asyncio.run(pull_bundle(db))

    assert result["bundle_changed"] is False
    assert result["not_modified"] is True
    # Warm cache: get_bundle_dict_raw at start of pull should not re-parse.
    assert loads == []
    assert get_bundle_dict(db)["organisation_id"] == 1


def test_pull_bundle_changed_body_refreshes_cache(monkeypatch, isolated_engine, db_session):
    from app.sync_service import pull_bundle

    db = db_session
    _seed(db, etag='"old"')
    get_bundle_dict(db)

    new_bundle = default_bundle()
    new_bundle["events"][0]["name"] = "FromCloud"

    async def fake_fetch(*, client=None, etag=None):
        return ConditionalGetResult(False, new_bundle, '"new"')

    monkeypatch.setattr("app.sync_service.fetch_bundle", fake_fetch)
    monkeypatch.setattr("app.sync_service.reconcile_bundle_lifecycle", lambda *_a, **_k: [])
    monkeypatch.setattr("app.sync_service.write_ota_freeze_from_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sync_service.clear_receipt_logo_cache", lambda: None)

    result = asyncio.run(pull_bundle(db))
    assert result["bundle_changed"] is True
    assert get_bundle_dict(db)["events"][0]["name"] == "FromCloud"
