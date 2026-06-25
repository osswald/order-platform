"""Cross-appliance operational snapshot via edge API."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    Event,
    HireCompany,
    Organisation,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _fixture_two_appliances() -> tuple[dict, dict, int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Ops {suffix}")
        db.add(company)
        db.flush()
        org = Organisation(
            name=f"Ops Org {suffix}",
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
        today = now.date()
        creds: list[dict] = []
        for name in ("Apollo", "Zeus"):
            appliance = Appliance(hire_company_id=company.id, type="server", name=name)
            db.add(appliance)
            db.flush()
            db.add(
                ApplianceLending(
                    appliance_id=appliance.id,
                    organisation_id=org.id,
                    start_date=today,
                    end_date=today,
                    returned_at=None,
                )
            )
            secret = f"secret-{name}-{suffix}"
            edge = ApplianceEdgeCredential(
                appliance_id=appliance.id,
                edge_client_id=f"cid-{name}-{suffix}",
                edge_secret_hash=get_password_hash(secret),
                status="active",
            )
            db.add(edge)
            db.flush()
            creds.append(
                {
                    "appliance_id": appliance.id,
                    "edge_client_id": edge.edge_client_id,
                    "edge_secret": secret,
                    "event_id": ev.id,
                }
            )
        db.commit()
        return creds[0], creds[1], org.id
    finally:
        db.close()


def _edge_headers(creds: dict) -> dict[str, str]:
    return {
        "X-Edge-Client-Id": creds["edge_client_id"],
        "X-Edge-Secret": creds["edge_secret"],
    }


def test_snapshot_visible_across_appliances_for_same_org():
    apollo, zeus, _org_id = _fixture_two_appliances()
    chunk_id = f"chunk-{uuid4().hex}"
    pushed = client.post(
        "/edge/v1/sync/operational/chunk",
        headers=_edge_headers(apollo),
        json={
            "chunk_id": chunk_id,
            "event_id": apollo["event_id"],
            "entity_type": "submission",
            "payload": {
                "client_order_id": "cross-appliance-order",
                "table_number": 8,
                "payment_status": "open",
                "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500}],
            },
        },
    )
    assert pushed.status_code == 200, pushed.text

    snapshot = client.get("/edge/v1/sync/operational/snapshot", headers=_edge_headers(zeus))
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert body["organisation_id"]
    events = body["events"]
    assert len(events) == 1
    assert events[0]["open_orders"][0]["client_order_id"] == "cross-appliance-order"
