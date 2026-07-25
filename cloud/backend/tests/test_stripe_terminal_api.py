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


def _edge_terminal_fixture(
    *,
    stripe_account_id: str | None = "acct_terminal_test",
    stripe_charges_enabled: bool = True,
) -> tuple[dict[str, str], int]:
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
            stripe_account_id=stripe_account_id,
            stripe_charges_enabled=stripe_charges_enabled,
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


def test_terminal_payment_intent_requires_connected_account():
    headers, event_id = _edge_terminal_fixture(stripe_account_id=None)
    r = client.post(
        "/edge/v1/terminal/payment-intents",
        headers=headers,
        json={"event_id": event_id, "amount_cents": 500},
    )
    assert r.status_code == 409, r.text


def test_terminal_payment_intent_requires_charges_enabled():
    headers, event_id = _edge_terminal_fixture(stripe_charges_enabled=False)
    r = client.post(
        "/edge/v1/terminal/payment-intents",
        headers=headers,
        json={"event_id": event_id, "amount_cents": 500},
    )
    assert r.status_code == 409, r.text


def _create_terminal_intent(monkeypatch, amount_cents: int) -> MagicMock:
    """Drive the edge endpoint through the real Stripe client wrapper."""
    headers, event_id = _edge_terminal_fixture()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    intent = MagicMock()
    intent.id = "pi_fee_test"
    intent.client_secret = "cs_test"
    intent.status = "requires_payment_method"
    intent.amount = amount_cents
    intent.currency = "chf"

    with patch("app.stripe_client.stripe.PaymentIntent.create", return_value=intent) as mock_create:
        r = client.post(
            "/edge/v1/terminal/payment-intents",
            headers=headers,
            json={"event_id": event_id, "amount_cents": amount_cents},
        )
    assert r.status_code == 200, r.text
    return mock_create


def test_terminal_payment_intent_charges_platform_fee(monkeypatch):
    mock_create = _create_terminal_intent(monkeypatch, 1000)

    kwargs = mock_create.call_args.kwargs
    assert kwargs["application_fee_amount"] == 2
    assert kwargs["amount"] == 1000
    assert kwargs["payment_method_types"] == ["card_present"]
    assert kwargs["stripe_account"] == "acct_terminal_test"


def test_terminal_payment_intent_omits_fee_when_it_rounds_to_zero(monkeypatch):
    mock_create = _create_terminal_intent(monkeypatch, 100)

    assert "application_fee_amount" not in mock_create.call_args.kwargs
