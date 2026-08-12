"""Conditional ETag responses for edge bundle and operational snapshot."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.edge_etag import etag_for_payload, etag_matches
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    Event,
    HireCompany,
    Organisation,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import add_lending, country_id_by_code

client = TestClient(app)


def test_etag_matches_quoted_and_weak_forms():
    etag = etag_for_payload({"a": 1})
    assert etag_matches(etag, etag)
    assert etag_matches(f"W/{etag}", etag)
    assert etag_matches(f' "other", {etag} ', etag)
    assert not etag_matches('"deadbeef"', etag)
    assert etag_matches("*", etag)


def _pair_live_event() -> tuple[str, str, int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        company = HireCompany(name=f"ETag HC {suffix}")
        db.add(company)
        db.flush()
        org = Organisation(
            name=f"ETag Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=company.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Live",
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(days=1),
            organisation_id=org.id,
        )
        db.add(ev)
        db.flush()
        appliance = Appliance(hire_company_id=company.id, type="server", name="ETag Node")
        db.add(appliance)
        db.flush()
        today = now.date()
        add_lending(
            db,
            appliance_id=appliance.id,
            organisation_id=org.id,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )
        secret = f"secret-{suffix}"
        cred = ApplianceEdgeCredential(
            appliance_id=appliance.id,
            edge_client_id=f"cid-{suffix}",
            edge_secret_hash=get_password_hash(secret),
            status="active",
        )
        db.add(cred)
        db.commit()
        return cred.edge_client_id, secret, ev.id
    finally:
        db.close()


def test_edge_bundle_etag_and_304():
    client_id, secret, _event_id = _pair_live_event()
    headers = {"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret}
    first = client.get("/edge/v1/bundle", headers=headers)
    assert first.status_code == 200, first.text
    etag = first.headers.get("etag")
    assert etag
    assert first.json().get("organisation_id") is not None

    second = client.get(
        "/edge/v1/bundle",
        headers={**headers, "If-None-Match": etag},
    )
    assert second.status_code == 304, second.text
    assert second.headers.get("etag") == etag
    assert not second.content


def test_operational_snapshot_etag_and_304():
    client_id, secret, event_id = _pair_live_event()
    headers = {"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret}
    first = client.get(
        "/edge/v1/sync/operational/snapshot",
        headers=headers,
        params={"event_id": event_id},
    )
    assert first.status_code == 200, first.text
    etag = first.headers.get("etag")
    assert etag

    second = client.get(
        "/edge/v1/sync/operational/snapshot",
        headers={**headers, "If-None-Match": etag},
        params={"event_id": event_id},
    )
    assert second.status_code == 304, second.text
    assert second.headers.get("etag") == etag


def test_edge_bundle_etag_changes_when_content_changes():
    from app.edge_etag import etag_for_payload

    a = etag_for_payload({"organisation_id": 1, "events": [{"id": 1}]})
    b = etag_for_payload({"organisation_id": 1, "events": [{"id": 1, "name": "changed"}]})
    assert a != b
    # server_time excluded by callers — same core payload → same etag
    assert etag_for_payload({"x": 1}) == etag_for_payload({"x": 1})
