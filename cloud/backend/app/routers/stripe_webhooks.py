"""Stripe webhook endpoint for Connect account and Terminal payment events."""

from __future__ import annotations

import logging
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Organisation
from ..stripe_connect_status import update_organisation_from_stripe_account_dict
from ..stripe_client import STRIPE_API_VERSION

router = APIRouter()
logger = logging.getLogger(__name__)


def _webhook_secret() -> str:
    secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="STRIPE_WEBHOOK_SECRET is not configured")
    return secret


@router.post("/webhooks")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header")

    stripe.api_version = STRIPE_API_VERSION
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, _webhook_secret())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc

    event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    data_object = None
    if isinstance(event, dict):
        data_object = (event.get("data") or {}).get("object")
    else:
        data_object = getattr(getattr(event, "data", None), "object", None)

    if event_type == "account.updated" and data_object:
        account_id = data_object.get("id") if isinstance(data_object, dict) else getattr(data_object, "id", None)
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
                db.commit()
    elif event_type == "payment_intent.succeeded" and data_object:
        pi_id = data_object.get("id") if isinstance(data_object, dict) else getattr(data_object, "id", None)
        logger.info("Stripe payment_intent.succeeded: %s", pi_id)

    return {"received": "true"}
