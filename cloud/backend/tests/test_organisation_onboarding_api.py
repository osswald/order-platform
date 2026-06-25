"""Organisation onboarding dismiss API."""

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed_tenant():
    db = SessionLocal()
    try:
        hc = HireCompany(name="Onboarding Tenant")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Onboarding Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email="onboarding-admin@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
                is_superuser=False,
            )
        )
        db.commit()
        return hc.id, org.id
    finally:
        db.close()


def _token() -> str:
    r = client.post("/auth/token", data={"username": "onboarding-admin@test.local", "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_dismiss_onboarding_hides_tasks():
    hire_company_id, org_id = _seed_tenant()
    headers = {
        "Authorization": f"Bearer {_token()}",
        "X-Hire-Company-Id": str(hire_company_id),
    }

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["onboarding"]["dismissed"] is False
    assert len(body["onboarding"]["tasks"]) > 0

    dismiss = client.post(f"/organisations/{org_id}/onboarding/dismiss", headers=headers)
    assert dismiss.status_code == 204

    summary2 = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary2.status_code == 200
    body2 = summary2.json()
    assert body2["onboarding"]["dismissed"] is True
    assert body2["onboarding"]["tasks"] == []

    dismiss2 = client.post(f"/organisations/{org_id}/onboarding/dismiss", headers=headers)
    assert dismiss2.status_code == 204


def test_complete_onboarding_task_marks_done():
    hire_company_id, org_id = _seed_tenant()
    headers = {
        "Authorization": f"Bearer {_token()}",
        "X-Hire-Company-Id": str(hire_company_id),
    }

    complete = client.post(
        f"/organisations/{org_id}/onboarding/tasks/create_waiter/complete",
        headers=headers,
    )
    assert complete.status_code == 204

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary.status_code == 200
    waiter_task = next(
        task for task in summary.json()["onboarding"]["tasks"] if task["id"] == "create_waiter"
    )
    assert waiter_task["done"] is True
    assert waiter_task["done_manually"] is True


def test_dismiss_onboarding_task_hides_task():
    hire_company_id, org_id = _seed_tenant()
    headers = {
        "Authorization": f"Bearer {_token()}",
        "X-Hire-Company-Id": str(hire_company_id),
    }

    dismiss = client.post(
        f"/organisations/{org_id}/onboarding/tasks/create_waiter/dismiss",
        headers=headers,
    )
    assert dismiss.status_code == 204

    summary = client.get(f"/organisations/{org_id}/dashboard-summary", headers=headers)
    assert summary.status_code == 200
    task_ids = [task["id"] for task in summary.json()["onboarding"]["tasks"]]
    assert "create_waiter" not in task_ids


def test_complete_unknown_onboarding_task_returns_404():
    hire_company_id, org_id = _seed_tenant()
    headers = {
        "Authorization": f"Bearer {_token()}",
        "X-Hire-Company-Id": str(hire_company_id),
    }

    complete = client.post(
        f"/organisations/{org_id}/onboarding/tasks/not-a-real-task/complete",
        headers=headers,
    )
    assert complete.status_code == 404
