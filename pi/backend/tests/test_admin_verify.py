"""Admin PIN verification against bundle admin_pin_hashes."""

import json

import pytest

from app.security import get_password_hash
from tests.fixtures_bundles import admin_bundle, bundle_copy


@pytest.fixture
def bundle():
    return bundle_copy(admin_bundle(pin_hashes=[get_password_hash("123456")]))


def test_admin_verify_success(client):
    r = client.post("/v1/admin/verify", json={"pin": "123456"})
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}


def test_admin_verify_wrong_pin(client):
    r = client.post("/v1/admin/verify", json={"pin": "000000"})
    assert r.status_code == 401


def test_admin_verify_no_hashes(client):
    import app.database as database

    from app.models import SyncedBundle

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

    from app.models import SyncedBundle

    Session = database.SessionLocal
    db = Session()
    updated = bundle_copy(
        admin_bundle(pin_hashes=["not-a-valid-bcrypt-hash", get_password_hash("654321")])
    )
    db.query(SyncedBundle).filter(SyncedBundle.id == 1).update(
        {SyncedBundle.json_body: json.dumps(updated)}
    )
    db.commit()
    db.close()

    r = client.post("/v1/admin/verify", json={"pin": "654321"})
    assert r.status_code == 200, r.text
