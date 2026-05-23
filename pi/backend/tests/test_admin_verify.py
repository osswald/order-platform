"""Admin PIN verification against bundle admin_pin_hashes."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import SyncedBundle
from app.security import get_password_hash


@pytest.fixture
def client():
    import app.database as database

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    Session = database.SessionLocal
    db = Session()
    bundle = {
        "organisation_id": 1,
        "admin_pin_hashes": [get_password_hash("123456")],
        "events": [],
    }
    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()
    db.close()

    from app.routers import edge_api

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[edge_api.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_admin_verify_success(client):
    r = client.post("/v1/admin/verify", json={"pin": "123456"})
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}


def test_admin_verify_wrong_pin(client):
    r = client.post("/v1/admin/verify", json={"pin": "000000"})
    assert r.status_code == 401


def test_admin_verify_no_hashes(client):
    import app.database as database

    Session = database.SessionLocal
    db = Session()
    db.query(SyncedBundle).filter(SyncedBundle.id == 1).update(
        {SyncedBundle.json_body: json.dumps({"organisation_id": 1, "events": []})}
    )
    db.commit()
    db.close()

    r = client.post("/v1/admin/verify", json={"pin": "123456"})
    assert r.status_code == 401
    assert r.json()["detail"] == "no_admin_pins_configured"


def test_admin_verify_skips_corrupt_hash(client):
    import app.database as database

    Session = database.SessionLocal
    db = Session()
    bundle = {
        "organisation_id": 1,
        "admin_pin_hashes": ["not-a-valid-bcrypt-hash", get_password_hash("654321")],
        "events": [],
    }
    db.query(SyncedBundle).filter(SyncedBundle.id == 1).update(
        {SyncedBundle.json_body: json.dumps(bundle)}
    )
    db.commit()
    db.close()

    r = client.post("/v1/admin/verify", json={"pin": "654321"})
    assert r.status_code == 200, r.text
