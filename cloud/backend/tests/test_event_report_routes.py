"""HTTP smoke tests for event report routes that delegate to service modules."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import Event, HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import ensure_country

client = TestClient(app)


def _report_fixture() -> tuple[str, int]:
    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        ch = ensure_country(db, "CH")
        hc = HireCompany(name=f"Report HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Report Org {suffix}",
            country_id=ch,
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Report Fest",
            status="prod",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_mode="pay_now",
            payment_types=["cash"],
        )
        db.add(ev)
        db.flush()
        db.add(
            User(
                email=f"report-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return f"report-{suffix}@test.local", ev.id
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_event_collective_bills_route():
    email, event_id = _report_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/collective-bills", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "collective_bills" in body
    assert isinstance(body["collective_bills"], list)


def test_event_collective_bill_pdf_route_smoke():
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.database import SessionLocal
    from app.event_collective_bills import upsert_collective_bill_from_payload
    from app.models import Appliance, EdgeSubmittedOrder, Event, HireCompany, Organisation, User
    from app.roles import ROLE_TENANT_ADMIN
    from app.security import get_password_hash

    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        ch = ensure_country(db, "CH")
        hc = HireCompany(name=f"Smoke HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(name=f"Smoke Org {suffix}", country_id=ch, hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Smoke Fest",
            status="prod",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_mode="pay_now",
            payment_types=["cash"],
        )
        db.add(ev)
        db.flush()
        appliance = Appliance(hire_company_id=hc.id, type="pi", name="Pi")
        db.add(appliance)
        db.flush()
        bill_uuid = f"cb-smoke-{suffix}"
        payload = {
            "collective_bill_uuid": bill_uuid,
            "collective_bill_name": "Smoke",
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 100, "additions": []}],
        }
        upsert_collective_bill_from_payload(
            db, event_id=ev.id, appliance_id=appliance.id, payload=payload
        )
        db.add(
            EdgeSubmittedOrder(
                client_order_id=f"smoke-{suffix}",
                appliance_id=appliance.id,
                organisation_id=org.id,
                event_id=ev.id,
                payload=payload,
            )
        )
        db.add(
            User(
                email=f"smoke-pdf-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        email = f"smoke-pdf-{suffix}@test.local"
        event_id = ev.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/collective-bills/{bill_uuid}/pdf", headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")


def test_event_sales_report_v3_route():
    email, event_id = _report_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/sales-report-v3", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "totals" in body


def test_event_stats_route():
    email, event_id = _report_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()
    r = client.get(
        f"/events/{event_id}/stats",
        params={"from": start, "to": end},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "totals" in body
    assert "article_timeline" in body
    assert body["article_timeline"]["bucket_count"] == 24


def test_event_payment_batches_v3_route():
    email, event_id = _report_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/payment-batches-v3", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "payment_batches" in body
    assert isinstance(body["payment_batches"], list)
