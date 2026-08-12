"""Handover-day active lending preference for edge and appliance status."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import Appliance, ApplianceEdgeCredential, HireCompany, Organisation, User
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import add_lending, country_id_by_code

client = TestClient(app)


def test_edge_prefers_lending_that_starts_today():
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Handover HC {suffix}")
        db.add(company)
        db.flush()
        org_leaving = Organisation(
            name=f"Leaving Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=company.id,
            currency="CHF",
        )
        org_arriving = Organisation(
            name=f"Arriving Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=company.id,
            currency="CHF",
        )
        db.add_all([org_leaving, org_arriving])
        db.flush()
        admin = User(
            email=f"handover-admin-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=company.id,
            is_superuser=False,
        )
        appliance = Appliance(hire_company_id=company.id, type="server", name="Handover Pi")
        db.add_all([admin, appliance])
        db.flush()
        today = datetime.now(UTC).date()
        add_lending(
            db,
            appliance_id=appliance.id,
            organisation_id=org_leaving.id,
            start_date=today - timedelta(days=3),
            end_date=today,
            hire_company_id=company.id,
            label="Leaving",
        )
        add_lending(
            db,
            appliance_id=appliance.id,
            organisation_id=org_arriving.id,
            start_date=today,
            end_date=today + timedelta(days=3),
            hire_company_id=company.id,
            label="Arriving",
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
        appliance_id = appliance.id
        arriving_id = org_arriving.id
        admin_email = admin.email
        client_id = cred.edge_client_id
    finally:
        db.close()

    bundle = client.get(
        "/edge/v1/bundle",
        headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret},
    )
    assert bundle.status_code == 200, bundle.text
    assert bundle.json()["organisation_id"] == arriving_id

    token_r = client.post("/auth/token", data={"username": admin_email, "password": "secret"})
    token = token_r.json()["access_token"]
    detail = client.get(f"/appliances/{appliance_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200
    assert detail.json()["lending_status"] == "lent"
    assert detail.json()["current_lending"]["organisation_id"] == arriving_id
