"""Stripe webhook handling."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
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
            country="CH",
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
