"""Tests for OTA freeze flag derived from synced bundle event status."""

from pathlib import Path

import pytest
from app.database import Base, init_test_schema
from app.models import SyncedBundle
from app.ota_freeze import (
    bundle_requires_ota_freeze,
    sync_ota_freeze_from_db,
    write_ota_freeze_from_bundle,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def ota_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OTA_STATE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app import database

    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine)
    Base.metadata.drop_all(bind=engine)
    init_test_schema()
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_bundle_requires_ota_freeze_any_prod():
    assert bundle_requires_ota_freeze({"events": [{"id": 1, "status": "test"}, {"id": 2, "status": "prod"}]})
    assert bundle_requires_ota_freeze({"events": [{"id": 1, "status": "PROD"}]})


def test_bundle_requires_ota_freeze_false_for_test_only_or_empty():
    assert not bundle_requires_ota_freeze(None)
    assert not bundle_requires_ota_freeze({})
    assert not bundle_requires_ota_freeze({"events": [{"id": 1, "status": "test"}]})
    assert not bundle_requires_ota_freeze({"events": [{"id": 1, "status": "archive"}]})


def test_write_ota_freeze_enables_for_prod(ota_dir: Path):
    write_ota_freeze_from_bundle({"events": [{"id": 1, "status": "prod"}]})
    assert (ota_dir / "freeze").read_text(encoding="utf-8").strip() == "1"


def test_write_ota_freeze_clears_for_test_only(ota_dir: Path):
    write_ota_freeze_from_bundle({"events": [{"id": 1, "status": "prod"}]})
    write_ota_freeze_from_bundle({"events": [{"id": 1, "status": "test"}]})
    assert (ota_dir / "freeze").read_text(encoding="utf-8").strip() == "0"


def test_sync_ota_freeze_from_db(ota_dir: Path, db):
    import json
    from datetime import UTC, datetime

    db.add(
        SyncedBundle(
            id=1,
            json_body=json.dumps({"organisation_id": 1, "events": [{"id": 9, "status": "prod"}]}),
            updated_at=datetime.now(UTC),
        )
    )
    db.commit()
    sync_ota_freeze_from_db(db)
    assert (ota_dir / "freeze").read_text(encoding="utf-8").strip() == "1"
