"""Local screensaver store and sync behaviour."""

from __future__ import annotations

import hashlib

import pytest
from app.event_lifecycle import purge_on_unpair, reconcile_bundle_lifecycle
from app.screensaver_store import (
    gc_screensaver_store,
    has_screensaver_file,
    list_local_shas,
    store_screensaver_bytes,
    wipe_screensaver_store,
)
from app.screensaver_sync import sync_screensaver_images


@pytest.fixture()
def screensaver_tmpdir(tmp_path, monkeypatch):
    root = tmp_path / "screensaver"
    monkeypatch.setenv("SCREENSAVER_DIR", str(root))
    wipe_screensaver_store()
    return root


def _png(sha_hint: bytes = b"a") -> tuple[str, bytes]:
    raw = b"\x89PNG\r\n\x1a\n" + sha_hint * 32
    return hashlib.sha256(raw).hexdigest(), raw


def test_sync_downloads_missing_skips_existing_and_gcs(screensaver_tmpdir, monkeypatch):
    import asyncio

    sha1, raw1 = _png(b"1")
    sha2, raw2 = _png(b"2")
    sha3, raw3 = _png(b"3")
    store_screensaver_bytes(sha1, raw1)
    store_screensaver_bytes(sha3, raw3)  # orphan — not in next manifest

    async def fake_fetch(sha256, *, client=None):
        assert sha256 == sha2
        return "image/png", raw2

    monkeypatch.setattr("app.screensaver_sync.fetch_screensaver_image", fake_fetch)

    bundle = {
        "organisation_id": 1,
        "screensaver_images": [
            {"sha256": sha1, "mime": "image/png"},
            {"sha256": sha2, "mime": "image/png"},
        ],
    }
    result = asyncio.run(sync_screensaver_images(bundle))
    assert sha1 in result["skipped"]
    assert sha2 in result["downloaded"]
    assert sha3 in result["deleted"]
    assert has_screensaver_file(sha1)
    assert has_screensaver_file(sha2)
    assert not has_screensaver_file(sha3)
    assert list_local_shas() == {sha1, sha2}


def test_wipe_on_org_change(screensaver_tmpdir, isolated_engine, db_session):
    sha, raw = _png(b"x")
    store_screensaver_bytes(sha, raw)
    assert has_screensaver_file(sha)
    reconcile_bundle_lifecycle(
        db_session,
        {"organisation_id": 1, "appliance_id": 10, "events": []},
        {"organisation_id": 2, "appliance_id": 10, "events": []},
    )
    assert list_local_shas() == set()


def test_wipe_on_unpair(screensaver_tmpdir, isolated_engine, db_session):
    sha, raw = _png(b"y")
    store_screensaver_bytes(sha, raw)
    purge_on_unpair(db_session)
    assert list_local_shas() == set()


def test_gc_keeps_manifest_only(screensaver_tmpdir):
    sha1, raw1 = _png(b"a")
    sha2, raw2 = _png(b"b")
    store_screensaver_bytes(sha1, raw1)
    store_screensaver_bytes(sha2, raw2)
    deleted = gc_screensaver_store({sha1})
    assert sha2 in deleted
    assert has_screensaver_file(sha1)
    assert not has_screensaver_file(sha2)


def test_gc_skips_invalid_keep_shas(screensaver_tmpdir):
    sha1, raw1 = _png(b"c")
    sha2, raw2 = _png(b"d")
    store_screensaver_bytes(sha1, raw1)
    store_screensaver_bytes(sha2, raw2)
    deleted = gc_screensaver_store({sha1, "not-a-sha", "", "xyz"})
    assert sha2 in deleted
    assert has_screensaver_file(sha1)
    assert not has_screensaver_file(sha2)
