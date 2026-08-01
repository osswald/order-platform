"""Edge bundle includes organisation SumUp readers."""

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
    SumupReader,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _pair_edge_credentials(*, with_readers: bool = False) -> tuple[str, str, int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"SumUp Bundle HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"SumUp Bundle Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        if with_readers:
            db.add(
                SumupReader(
                    organisation_id=org.id,
                    sumup_reader_id="rdr_test1234567890123456789012",
                    label="Terrasse",
                    status="paired",
                )
            )
            db.add(
                SumupReader(
                    organisation_id=org.id,
                    sumup_reader_id="rdr_test9876543210987654321098",
                    label="Bar",
                    status="paired",
                )
            )
        db.add(
            User(
                email=f"sumup-bundle-{suffix}@test.local",
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
            edge_client_id=f"client-{suffix}",
            edge_secret_hash=get_password_hash("edge-secret"),
            label="SD",
            status="active",
        )
        db.add(cred)
        db.commit()
        return cred.edge_client_id, "edge-secret", org.id
    finally:
        db.close()


def test_edge_bundle_includes_empty_sumup_readers_without_org_readers():
    client_id, secret, _org_id = _pair_edge_credentials(with_readers=False)
    response = client.get(
        "/edge/v1/bundle",
        headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("sumup_readers") == []


def test_edge_bundle_includes_org_sumup_readers():
    client_id, secret, _org_id = _pair_edge_credentials(with_readers=True)
    response = client.get(
        "/edge/v1/bundle",
        headers={"X-Edge-Client-Id": client_id, "X-Edge-Secret": secret},
    )
    assert response.status_code == 200, response.text
    readers = response.json().get("sumup_readers")
    assert readers == [
        {"sumup_reader_id": "rdr_test9876543210987654321098", "label": "Bar"},
        {"sumup_reader_id": "rdr_test1234567890123456789012", "label": "Terrasse"},
    ]
