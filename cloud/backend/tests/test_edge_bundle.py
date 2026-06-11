"""Edge bundle payload shape for paired appliances."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash

client = TestClient(app)


def _pair_edge_credentials() -> tuple[str, str]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Bundle HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(name=f"Bundle Org {suffix}", country="CH", hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        db.add(
            User(
                email=f"bundle-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        appliance = Appliance(
            hire_company_id=hc.id,
            type="server",
            name="Server Node",
            ip_address="10.0.0.1",
        )
        db.add(appliance)
        db.flush()
        today = datetime.now(timezone.utc).date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today - timedelta(days=1),
                end_date=today + timedelta(days=1),
            )
        )
        cred = ApplianceEdgeCredential(
            appliance_id=appliance.id,
            edge_client_id=f"client-{suffix}",
            edge_secret_hash=get_password_hash("edge-secret"),
            label="SD",
            status="active",
        )
        db.add(cred)
        db.commit()
        return cred.edge_client_id, "edge-secret"
    finally:
        db.close()


def test_edge_bundle_returns_events_and_organisation():
    client_id, secret = _pair_edge_credentials()
    response = client.get(
        "/edge/v1/bundle",
        headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "organisation_id" in body
    assert isinstance(body.get("events"), list)
