"""Stripe webhook handling."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from tests.helpers import country_id_by_code
from app.main import app
from app.models import HireCompany, Organisation

client = TestClient(app)


@pytest.fixture(autouse=True)
def _webhook_secret(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")


def _seed_org_with_stripe_account(account_id: str = "acct_test123") -> int:
    db = SessionLocal()
    try:
        hc = HireCompany(name="Stripe HC")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="Stripe Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
            stripe_account_id=account_id,
            stripe_charges_enabled=False,
            stripe_payouts_enabled=False,
            stripe_details_submitted=False,
        )
        db.add(org)
        db.commit()
        return org.id
    finally:
        db.close()


def test_webhook_account_updated_updates_organisation():
    org_id = _seed_org_with_stripe_account()
    event = {
        "id": "evt_account_updated_test",
        "type": "account.updated",
        "data": {
            "object": {
                "id": "acct_test123",
                "charges_enabled": True,
                "payouts_enabled": True,
                "details_submitted": True,
            }
        },
    }

    with patch("app.routers.stripe_webhooks.stripe.Webhook.construct_event", return_value=event):
        r = client.post(
            "/stripe/webhooks",
            data=json.dumps(event),
            headers={"Stripe-Signature": "test_sig"},
        )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        assert org.stripe_charges_enabled is True
        assert org.stripe_payouts_enabled is True
        assert org.stripe_details_submitted is True
        assert org.stripe_account_updated_at is not None
    finally:
        db.close()


def test_stripe_webhook_duplicate_event_is_ignored():
    org_id = _seed_org_with_stripe_account()
    event = {
        "id": "evt_duplicate_test",
        "type": "account.updated",
        "data": {
            "object": {
                "id": "acct_test123",
                "charges_enabled": True,
                "payouts_enabled": True,
                "details_submitted": True,
            }
        },
    }

    with patch("app.routers.stripe_webhooks.stripe.Webhook.construct_event", return_value=event):
        first = client.post(
            "/stripe/webhooks",
            data=json.dumps(event),
            headers={"Stripe-Signature": "test_sig"},
        )
        second = client.post(
            "/stripe/webhooks",
            data=json.dumps(event),
            headers={"Stripe-Signature": "test_sig"},
        )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json().get("duplicate") == "true"

    from app.models import StripeWebhookEvent

    db = SessionLocal()
    try:
        count = (
            db.query(StripeWebhookEvent)
            .filter(StripeWebhookEvent.stripe_event_id == "evt_duplicate_test")
            .count()
        )
        assert count == 1
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        assert org.stripe_charges_enabled is True
    finally:
        db.close()


def test_payment_intent_succeeded_persists_webhook_event():
    event = {
        "id": "evt_pi_success",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_abc123",
                "metadata": {"client_order_id": "order-1", "event_id": "42"},
            }
        },
    }
    with patch("app.routers.stripe_webhooks.stripe.Webhook.construct_event", return_value=event):
        r = client.post(
            "/stripe/webhooks",
            data=json.dumps(event),
            headers={"Stripe-Signature": "test_sig"},
        )
    assert r.status_code == 200, r.text

    from app.models import StripeWebhookEvent

    db = SessionLocal()
    try:
        row = (
            db.query(StripeWebhookEvent)
            .filter(StripeWebhookEvent.stripe_event_id == "evt_pi_success")
            .first()
        )
        assert row is not None
        assert row.payment_intent_id == "pi_abc123"
        assert row.metadata_json["client_order_id"] == "order-1"
    finally:
        db.close()


def test_webhook_rejects_missing_signature():
    r = client.post("/stripe/webhooks", data=b"{}")
    assert r.status_code == 400


def test_webhook_requires_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    with patch("app.routers.stripe_webhooks.stripe.Webhook.construct_event", return_value={"type": "ping"}):
        r = client.post(
            "/stripe/webhooks",
            data=b"{}",
            headers={"Stripe-Signature": "sig"},
        )
    assert r.status_code == 503
