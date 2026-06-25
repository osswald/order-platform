"""Organisation position comment presets and feature flag."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    HireCompany,
    Organisation,
    OrganisationPositionComment,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed_tenant() -> int:
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"PosComment HC {uuid4().hex[:8]}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="PosComment Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email=f"poscomment-{uuid4().hex[:8]}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id
    finally:
        db.close()


def _token() -> str:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email.like("poscomment-%@test.local"))
            .order_by(User.id.desc())
            .first()
        )
        email = user.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_position_comments_crud_and_org_flag():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    list_empty = client.get(f"/organisations/{org_id}/position-comments", headers=headers)
    assert list_empty.status_code == 200
    assert list_empty.json() == []

    created = client.post(
        f"/organisations/{org_id}/position-comments",
        headers=headers,
        json={"text": "ohne Zwiebeln", "sort_order": 1},
    )
    assert created.status_code == 201, created.text
    preset_id = created.json()["id"]
    assert created.json()["text"] == "ohne Zwiebeln"

    updated = client.put(
        f"/organisations/{org_id}/position-comments/{preset_id}",
        headers=headers,
        json={"text": "extra scharf"},
    )
    assert updated.status_code == 200
    assert updated.json()["text"] == "extra scharf"

    flag_on = client.put(
        f"/organisations/{org_id}",
        headers=headers,
        json={"position_comments_enabled": True},
    )
    assert flag_on.status_code == 200
    assert flag_on.json()["position_comments_enabled"] is True

    listed = client.get(f"/organisations/{org_id}/position-comments", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = client.delete(
        f"/organisations/{org_id}/position-comments/{preset_id}",
        headers=headers,
    )
    assert deleted.status_code == 204


def test_edge_bundle_includes_position_comments_when_enabled():
    db = SessionLocal()
    try:
        suffix = uuid4().hex[:8]
        hc = HireCompany(name=f"Bundle PC HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Bundle PC Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
            position_comments_enabled=True,
        )
        db.add(org)
        db.flush()
        db.add(OrganisationPositionComment(organisation_id=org.id, text="medium", sort_order=0))
        appliance = Appliance(
            hire_company_id=hc.id,
            type="server",
            name="Server",
            ip_address="10.0.0.2",
        )
        db.add(appliance)
        db.flush()
        today = datetime.now(UTC).date()
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
            edge_client_id=f"pc-client-{suffix}",
            edge_secret_hash=get_password_hash("edge-secret"),
            status="active",
        )
        db.add(cred)
        db.commit()
        client_id = cred.edge_client_id
    finally:
        db.close()

    response = client.get(
        "/edge/v1/bundle",
        headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": "edge-secret"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["position_comments_enabled"] is True
    assert len(data["position_comment_presets"]) == 1
    assert data["position_comment_presets"][0]["text"] == "medium"
