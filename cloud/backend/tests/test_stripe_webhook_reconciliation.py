"""Documents intentional payment_intent.succeeded handling."""

from pathlib import Path


def test_payment_intent_webhook_documents_intentional_no_reconciliation():
    source = Path(__file__).resolve().parents[1].joinpath("app/routers/stripe_webhooks.py").read_text(
        encoding="utf-8"
    )
    assert "payment_intent.succeeded" in source
    assert "Reconciliation is handled on the edge device" in source
