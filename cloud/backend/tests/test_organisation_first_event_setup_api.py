"""Organisation first-event setup state API."""

from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.main import app
from app.models import (
    Article,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventStation,
    EventWaiter,
    HireCompany,
    Organisation,
    User,
    Waiter,
)
from app.roles import ROLE_ORGANISATION_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed(*, with_org_admin: bool = False):
    db = SessionLocal()
    try:
        hc = HireCompany(name="First Event Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="First Event Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="first-event-tenant@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
        )
        if with_org_admin:
            org_admin = User(
                email="first-event-org-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_ORGANISATION_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
            db.add(org_admin)
            db.flush()
            org_admin.organisations = [org]
        db.commit()
        return hc.id, org.id
    finally:
        db.close()


def _token(email: str = "first-event-tenant@test.local") -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _headers(hire_company_id: int, email: str = "first-event-tenant@test.local"):
    return {
        "Authorization": f"Bearer {_token(email)}",
        "X-Hire-Company-Id": str(hire_company_id),
    }


def test_first_event_setup_defaults_available():
    hire_company_id, org_id = _seed()
    headers = _headers(hire_company_id)

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    setup = summary.json()["first_event_setup"]
    assert setup["available"] is True
    assert setup["completed"] is False
    assert setup["dismissed"] is False
    assert setup["in_progress_event_id"] is None


def test_dismiss_first_event_setup_hides_cta():
    hire_company_id, org_id = _seed()
    headers = _headers(hire_company_id)

    dismiss = client.post(f"/organisations/{org_id}/first-event-setup/dismiss", headers=headers)
    assert dismiss.status_code == 204, dismiss.text

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    setup = summary.json()["first_event_setup"]
    assert setup["dismissed"] is True
    assert setup["available"] is False
    assert setup["completed"] is False

    dismiss2 = client.post(f"/organisations/{org_id}/first-event-setup/dismiss", headers=headers)
    assert dismiss2.status_code == 204


def test_complete_first_event_setup_hides_cta():
    hire_company_id, org_id = _seed()
    headers = _headers(hire_company_id)

    complete = client.post(f"/organisations/{org_id}/first-event-setup/complete", headers=headers)
    assert complete.status_code == 204, complete.text

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    setup = summary.json()["first_event_setup"]
    assert setup["completed"] is True
    assert setup["available"] is False


def test_patch_in_progress_event_id():
    hire_company_id, org_id = _seed()
    headers = _headers(hire_company_id)

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        event = Event(
            name="Wizard Event",
            status="config",
            start=now + timedelta(days=1),
            end=now + timedelta(days=2),
            organisation_id=org_id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(event)
        db.commit()
        event_id = event.id
    finally:
        db.close()

    patch = client.patch(
        f"/organisations/{org_id}/first-event-setup",
        headers=headers,
        json={"in_progress_event_id": event_id},
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["in_progress_event_id"] == event_id
    assert body["available"] is True

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary.json()["first_event_setup"]["in_progress_event_id"] == event_id

    clear = client.patch(
        f"/organisations/{org_id}/first-event-setup",
        headers=headers,
        json={"in_progress_event_id": None},
    )
    assert clear.status_code == 200, clear.text
    assert clear.json()["in_progress_event_id"] is None


def test_patch_rejects_event_from_other_org():
    hire_company_id, org_id = _seed()
    headers = _headers(hire_company_id)

    db = SessionLocal()
    try:
        other = Organisation(
            name="Other Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hire_company_id,
            currency="CHF",
        )
        db.add(other)
        db.flush()
        now = datetime.now(UTC)
        event = Event(
            name="Other Event",
            status="config",
            start=now + timedelta(days=1),
            end=now + timedelta(days=2),
            organisation_id=other.id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(event)
        db.commit()
        other_event_id = event.id
    finally:
        db.close()

    patch = client.patch(
        f"/organisations/{org_id}/first-event-setup",
        headers=headers,
        json={"in_progress_event_id": other_event_id},
    )
    assert patch.status_code == 422


def test_first_event_setup_org_scoped_for_org_admin():
    hire_company_id, org_id = _seed(with_org_admin=True)
    tenant_headers = _headers(hire_company_id)
    org_headers = _headers(hire_company_id, "first-event-org-admin@test.local")

    dismiss = client.post(
        f"/organisations/{org_id}/first-event-setup/dismiss",
        headers=tenant_headers,
    )
    assert dismiss.status_code == 204

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=org_headers)
    assert summary.status_code == 200
    assert summary.json()["first_event_setup"]["dismissed"] is True
    assert summary.json()["first_event_setup"]["available"] is False


def test_auto_marks_complete_when_minimally_configured_event_exists():
    hire_company_id, org_id = _seed()
    headers = _headers(hire_company_id)

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        cat = ArticleCategory(name="Bar", organisation_id=org_id)
        db.add(cat)
        db.flush()
        article = Article(
            name="Beer",
            label="Beer",
            price=5.0,
            article_category_id=cat.id,
            is_addition=False,
            is_active=True,
        )
        db.add(article)
        waiter = Waiter(name="Alex", pin="1234", organisation_id=org_id)
        db.add(waiter)
        db.flush()
        event = Event(
            name="Ready Fest",
            status="config",
            start=now + timedelta(days=1),
            end=now + timedelta(days=2),
            organisation_id=org_id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(event)
        db.flush()
        station = EventStation(name="Bar", event_id=event.id)
        station.articles = [article]
        db.add(station)
        db.add(
            EventWaiter(
                event_id=event.id,
                name="Alex",
                pin="1234",
                source_waiter_id=waiter.id,
            )
        )
        db.add(
            EventAppLayout(
                event_id=event.id,
                name="Default",
                is_default=True,
                grid_width=2,
                grid_height=2,
            )
        )
        db.commit()
    finally:
        db.close()

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    setup = summary.json()["first_event_setup"]
    assert setup["completed"] is True
    assert setup["available"] is False
