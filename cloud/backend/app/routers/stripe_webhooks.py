"""Stripe webhook endpoint for Connect account and Terminal payment events."""

from __future__ import annotations

import logging
import os
from typing import Any

import stripe
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ..deps import get_db
from ..db_errors import commit_or_raise
from ..i18n.errors import api_error
from ..models import Organisation, StripeWebhookEvent
from ..stripe_client import STRIPE_API_VERSION
from ..stripe_connect_status import update_organisation_from_stripe_account_dict

router = APIRouter()
logger = logging.getLogger(__name__)


def _webhook_secret() -> str:
    secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise api_error("stripe_webhook_secret_missing", status.HTTP_503_SERVICE_UNAVAILABLE)
    return secret


def _event_field(event: Any, key: str, default: Any = None) -> Any:
    if isinstance(event, dict):
        return event.get(key, default)
    return getattr(event, key, default)


def _data_object(event: Any) -> Any:
    data = _event_field(event, "data") or {}
    if isinstance(data, dict):
        return data.get("object")
    return getattr(data, "object", None)


@router.post("/webhooks")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise api_error("stripe_signature_missing", status.HTTP_400_BAD_REQUEST)

    stripe.api_version = STRIPE_API_VERSION
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, _webhook_secret())
    except ValueError as exc:
        raise api_error("stripe_invalid_payload", status.HTTP_400_BAD_REQUEST) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise api_error("stripe_invalid_signature", status.HTTP_400_BAD_REQUEST) from exc

    event_id = _event_field(event, "id")
    if not event_id:
        raise api_error("stripe_invalid_payload", status.HTTP_400_BAD_REQUEST)

    existing = (
        db.query(StripeWebhookEvent)
        .filter(StripeWebhookEvent.stripe_event_id == str(event_id))
        .first()
    )
    if existing:
        return {"received": "true", "duplicate": "true"}

    event_type = _event_field(event, "type")
    data_object = _data_object(event)

    payment_intent_id = None
    metadata_json = None

    if event_type == "account.updated" and data_object:
        account_id = (
            data_object.get("id") if isinstance(data_object, dict) else getattr(data_object, "id", None)
        )
        if account_id:
            organisation = (
                db.query(Organisation).filter(Organisation.stripe_account_id == str(account_id)).first()
            )
            if organisation:
                if isinstance(data_object, dict):
                    update_organisation_from_stripe_account_dict(organisation, data_object)
                else:
                    from ..stripe_connect_status import update_organisation_from_stripe_account

                    update_organisation_from_stripe_account(organisation, data_object)
    elif event_type == "payment_intent.succeeded" and data_object:
        # Reconciliation is handled on the edge device: Pi polls GET /edge/v1/terminal/
        # payment-intents/{id} after card-present capture. This webhook is an audit trail
        # for Connect reporting and duplicate-safe bookkeeping of Stripe retries.
        payment_intent_id = (
            data_object.get("id") if isinstance(data_object, dict) else getattr(data_object, "id", None)
        )
        raw_metadata = (
            data_object.get("metadata")
            if isinstance(data_object, dict)
            else getattr(data_object, "metadata", None)
        )
        if isinstance(raw_metadata, dict):
            metadata_json = {str(k): str(v) for k, v in raw_metadata.items() if v is not None}
        logger.info("Stripe payment_intent.succeeded: %s metadata=%s", payment_intent_id, metadata_json)

    db.add(
        StripeWebhookEvent(
            stripe_event_id=str(event_id),
            event_type=str(event_type or ""),
            payment_intent_id=str(payment_intent_id) if payment_intent_id else None,
            metadata_json=metadata_json,
        )
    )
    commit_or_raise(db)
    return {"received": "true"}
