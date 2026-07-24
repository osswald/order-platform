"""Stripe Terminal edge HTTP API."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
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


def _edge_terminal_fixture() -> tuple[dict[str, str], int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Terminal HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Terminal Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
            stripe_account_id="acct_terminal_test",
            stripe_charges_enabled=True,
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
            payment_types=["cash", "stripe_terminal"],
        )
        db.add(ev)
        db.flush()
        appliance = Appliance(hire_company_id=hc.id, type="server", name="Pi")
        db.add(appliance)
        db.flush()
        today = now.date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today,
                end_date=today,
                returned_at=None,
            )
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
        return (
            {
                "X-Edge-Client-Id": cred.edge_client_id,
                "X-Edge-Secret": secret,
            },
            ev.id,
        )
    finally:
        db.close()


@patch("app.routers.stripe_terminal.stripe_client.create_terminal_connection_token")
def test_terminal_connection_token(mock_create_token):
    headers, event_id = _edge_terminal_fixture()
    token = MagicMock()
    token.secret = "pst_test_secret"
    mock_create_token.return_value = token

    r = client.post(
        "/edge/v1/terminal/connection-token",
        headers=headers,
        json={"event_id": event_id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["secret"] == "pst_test_secret"
    mock_create_token.assert_called_once()


@patch("app.routers.stripe_terminal.stripe_client.create_terminal_payment_intent")
def test_terminal_create_payment_intent(mock_create_intent):
    headers, event_id = _edge_terminal_fixture()
    intent = MagicMock()
    intent.id = "pi_test123"
    intent.client_secret = "cs_test"
    intent.status = "requires_payment_method"
    intent.amount = 500
    intent.currency = "chf"
    mock_create_intent.return_value = intent

    r = client.post(
        "/edge/v1/terminal/payment-intents",
        headers=headers,
        json={"event_id": event_id, "amount_cents": 500},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == "pi_test123"
    assert body["amount_cents"] == 500


@patch("app.routers.stripe_terminal.stripe_client.create_terminal_payment_intent")
def test_terminal_payment_intent_system_metadata_wins(mock_create_intent):
    headers, event_id = _edge_terminal_fixture()
    intent = MagicMock()
    intent.id = "pi_meta"
    intent.client_secret = "cs"
    intent.status = "requires_payment_method"
    intent.amount = 100
    intent.currency = "chf"
    mock_create_intent.return_value = intent

    r = client.post(
        "/edge/v1/terminal/payment-intents",
        headers=headers,
        json={
            "event_id": event_id,
            "amount_cents": 100,
            "metadata": {"event_id": "99999", "organisation_id": "0"},
        },
    )
    assert r.status_code == 200, r.text
    meta = mock_create_intent.call_args.kwargs["metadata"]
    assert meta["event_id"] == str(event_id)
    assert meta["organisation_id"] != "0"


@patch("app.routers.stripe_terminal.stripe_client.retrieve_terminal_payment_intent")
def test_terminal_read_rejects_foreign_event_metadata(mock_retrieve):
    headers, event_id = _edge_terminal_fixture()
    intent = MagicMock()
    intent.id = "pi_other"
    intent.client_secret = "cs"
    intent.status = "succeeded"
    intent.amount = 100
    intent.currency = "chf"
    intent.metadata = {"event_id": "99999"}
    mock_retrieve.return_value = intent

    r = client.get(
        f"/edge/v1/terminal/payment-intents/pi_other?event_id={event_id}",
        headers=headers,
    )
    assert r.status_code == 404
