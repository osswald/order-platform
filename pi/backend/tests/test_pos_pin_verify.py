"""Waiter and cash-register PIN verification (server-side, hashed bundle)."""

from app.security import get_password_hash
from tests.fixtures_bundles import bundle_copy, cash_register_bundle, default_bundle


def _waiter_bundle(pin_plain: str = "1234") -> dict:
    bundle = default_bundle()
    event = bundle["events"][0]
    event["configuration"] = {
        "stations": [],
        "event_waiters": [
            {
                "uuid": "w-1",
                "name": "Anna",
                "pin_hash": get_password_hash(pin_plain),
            }
        ],
        "cash_registers": [],
    }
    return bundle


def test_waiter_pin_verify_success(client):
    import app.database as database
    from app.models import SyncedBundle

    bundle = bundle_copy(_waiter_bundle("1234"))
    db = database.SessionLocal()
    db.query(SyncedBundle).filter(SyncedBundle.id == 1).update(
        {SyncedBundle.json_body: __import__("json").dumps(bundle)}
    )
    db.commit()
    db.close()

    r = client.post(
        "/v1/auth/waiter/verify",
        json={"event_id": 1, "waiter_uuid": "w-1", "pin": "1234"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["name"] == "Anna"


def test_waiter_pin_verify_wrong_pin(client):
    import app.database as database
    from app.models import SyncedBundle

    bundle = bundle_copy(_waiter_bundle("1234"))
    db = database.SessionLocal()
    db.query(SyncedBundle).filter(SyncedBundle.id == 1).update(
        {SyncedBundle.json_body: __import__("json").dumps(bundle)}
    )
    db.commit()
    db.close()

    r = client.post(
        "/v1/auth/waiter/verify",
        json={"event_id": 1, "waiter_uuid": "w-1", "pin": "9999"},
    )
    assert r.status_code == 401


def test_register_pin_verify_success(client):
    import app.database as database
    from app.models import SyncedBundle

    bundle = bundle_copy(cash_register_bundle())
    db = database.SessionLocal()
    db.query(SyncedBundle).filter(SyncedBundle.id == 1).update(
        {SyncedBundle.json_body: __import__("json").dumps(bundle)}
    )
    db.commit()
    db.close()

    r = client.post(
        "/v1/auth/register/verify",
        json={"event_id": 1, "register_uuid": "reg-1", "pin": "0000"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Hauptkasse"
