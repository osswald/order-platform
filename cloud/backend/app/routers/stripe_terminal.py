"""Device-authenticated Stripe Terminal endpoints for Pi/Android clients."""

from __future__ import annotations

import re
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..deps import get_db
from ..event_status import ORDER_ACCEPT_STATUSES
from ..models import Event, Organisation
from ..payment_types_config import payment_types_from_event
from ..stripe_client import StripeConfigError
from .. import stripe_client
from .edge import ApplianceEdgeContext, get_edge_server_appliance, _load_event_for_org

router = APIRouter()
STRIPE_TERMINAL_PAYMENT_TYPE = "stripe_terminal"
PAYMENT_INTENT_ID_PATTERN = re.compile(r"^pi_[A-Za-z0-9_]+$")


class TerminalConnectionTokenCreate(BaseModel):
    event_id: int


class TerminalConnectionTokenRead(BaseModel):
    secret: str


class TerminalPaymentIntentCreate(BaseModel):
    event_id: int
    amount_cents: int = Field(..., gt=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    client_order_id: str | None = Field(None, max_length=64)
    idempotency_key: str | None = Field(None, max_length=255)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class TerminalPaymentIntentRead(BaseModel):
    id: str
    client_secret: str | None = None
    status: str
    amount_cents: int
    currency: str


def _stripe_error(exc: Exception) -> HTTPException:
    if isinstance(exc, StripeConfigError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, stripe.error.StripeError):
        message = getattr(exc, "user_message", None) or str(exc)
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe request failed")


def _stripe_attr(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _intent_response(intent) -> TerminalPaymentIntentRead:
    return TerminalPaymentIntentRead(
        id=str(_stripe_attr(intent, "id")),
        client_secret=_stripe_attr(intent, "client_secret"),
        status=str(_stripe_attr(intent, "status")),
        amount_cents=int(_stripe_attr(intent, "amount", 0)),
        currency=str(_stripe_attr(intent, "currency", "")).upper(),
    )


def _terminal_organisation_for_event(db: Session, ctx: ApplianceEdgeContext, event_id: int) -> tuple[Event, Organisation]:
    event = _load_event_for_org(db, event_id, ctx.organisation_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for organisation")

    ev_status = (event.status or "config").lower()
    if ev_status not in ORDER_ACCEPT_STATUSES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Event status {ev_status} does not accept payments")

    if STRIPE_TERMINAL_PAYMENT_TYPE not in payment_types_from_event(event):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Stripe Terminal is not enabled for this event")

    organisation = event.organisation
    if not organisation or not organisation.stripe_account_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organisation has no connected Stripe account")
    if not organisation.stripe_charges_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connected Stripe account is not ready for charges")
    return event, organisation


@router.post("/v1/terminal/connection-token", response_model=TerminalConnectionTokenRead)
def create_terminal_connection_token(
    body: TerminalConnectionTokenCreate,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
) -> TerminalConnectionTokenRead:
    _, organisation = _terminal_organisation_for_event(db, ctx, body.event_id)
    try:
        token = stripe_client.create_terminal_connection_token(account_id=organisation.stripe_account_id)
    except Exception as exc:
        raise _stripe_error(exc) from exc
    return TerminalConnectionTokenRead(secret=str(_stripe_attr(token, "secret")))


@router.post("/v1/terminal/payment-intents", response_model=TerminalPaymentIntentRead)
def create_terminal_payment_intent(
    body: TerminalPaymentIntentCreate,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
) -> TerminalPaymentIntentRead:
    event, organisation = _terminal_organisation_for_event(db, ctx, body.event_id)
    currency = (body.currency or event.currency or "CHF").upper()
    metadata = {
        "event_id": str(event.id),
        "organisation_id": str(organisation.id),
        "appliance_id": str(ctx.appliance.id),
        "hire_company_id": str(organisation.hire_company_id),
        **{str(k): str(v) for k, v in body.metadata.items() if v is not None},
    }
    if body.client_order_id:
        metadata["client_order_id"] = body.client_order_id
    try:
        intent = stripe_client.create_terminal_payment_intent(
            account_id=organisation.stripe_account_id,
            amount_cents=body.amount_cents,
            currency=currency,
            metadata=metadata,
            idempotency_key=body.idempotency_key,
        )
    except Exception as exc:
        raise _stripe_error(exc) from exc
    return _intent_response(intent)


@router.get("/v1/terminal/payment-intents/{payment_intent_id}", response_model=TerminalPaymentIntentRead)
def read_terminal_payment_intent(
    payment_intent_id: str,
    event_id: int = Query(...),
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
) -> TerminalPaymentIntentRead:
    if not PAYMENT_INTENT_ID_PATTERN.match(payment_intent_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid PaymentIntent id")
    _, organisation = _terminal_organisation_for_event(db, ctx, event_id)
    try:
        intent = stripe_client.retrieve_terminal_payment_intent(
            account_id=organisation.stripe_account_id,
            payment_intent_id=payment_intent_id,
        )
    except Exception as exc:
        raise _stripe_error(exc) from exc
    return _intent_response(intent)
