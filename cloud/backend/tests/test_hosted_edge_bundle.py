"""Hosted virtual appliance edge bundle."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    Event,
    HireCompany,
    HostedPiInstance,
    Organisation,
)
from app.security import get_password_hash

client = TestClient(app)


def test_hosted_bundle_includes_config_event():
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Hosted Bundle HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(name=f"Hosted Bundle Org {suffix}", country="CH", hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        now = datetime.now(timezone.utc)
        event = Event(
            name="Future Config",
            status="config",
            start=now + timedelta(days=30),
            end=now + timedelta(days=31),
            organisation_id=org.id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(event)
        db.flush()
        appliance = Appliance(
            hire_company_id=hc.id,
            type="server",
            name="Cloud-Pi",
            is_hosted_virtual=True,
        )
        db.add(appliance)
        db.flush()
        today = now.date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today,
                end_date=today + timedelta(days=1),
            )
        )
        cred = ApplianceEdgeCredential(
            appliance_id=appliance.id,
            edge_client_id=f"hosted-{suffix}",
            edge_secret_hash=get_password_hash("edge-secret"),
            label="hosted",
            status="active",
        )
        db.add(cred)
        db.flush()
        db.add(
            HostedPiInstance(
                event_id=event.id,
                organisation_id=org.id,
                hire_company_id=hc.id,
                appliance_id=appliance.id,
                edge_credential_id=cred.id,
                subdomain_slug=suffix[:12],
                status="running",
                expires_at=now + timedelta(hours=24),
            )
        )
        db.commit()
        client_id = cred.edge_client_id
        event_id = event.id
    finally:
        db.close()

    response = client.get(
        "/edge/v1/bundle",
        headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": "edge-secret"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["events"]) == 1
    assert body["events"][0]["id"] == event_id
    assert body["events"][0]["status"] == "config"
