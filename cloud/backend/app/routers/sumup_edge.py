"""Device-authenticated SumUp Solo reader checkout endpoints for Pi clients."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .. import sumup_client
from ..currency import event_currency, organisation_currency
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..event_status import ORDER_ACCEPT_STATUSES
from ..i18n.errors import api_error
from ..models import Event, Organisation, SumupCheckout, SumupReader
from ..payment_types_config import payment_types_from_event
from ..sumup_checkout_state import apply_checkout_payload, normalize_checkout_status
from ..sumup_client import sumup_error
from ..sumup_tokens import get_valid_access_token
from .edge import ApplianceEdgeContext, _load_event_for_org, get_edge_server_appliance

router = APIRouter()
SUMUP_CONNECTED_PAYMENT_TYPE = "sumup_connected"


class SumupCheckoutCreate(BaseModel):
    event_id: int
    amount_cents: int = Field(..., gt=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    reader_id: str = Field(..., min_length=1, max_length=64)
    client_order_id: str | None = Field(None, max_length=64)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class SumupCheckoutRead(BaseModel):
    checkout_id: str
    status: str
    transaction_id: str | None = None


class SumupTerminateBody(BaseModel):
    event_id: int
    reader_id: str = Field(..., min_length=1, max_length=64)


class SumupTerminateResponse(BaseModel):
    ok: bool = True


def _sumup_organisation_for_event(
    db: Session,
    ctx: ApplianceEdgeContext,
    event_id: int,
) -> tuple[Event, Organisation]:
    event = _load_event_for_org(db, event_id, ctx.organisation_id)
    if not event:
        raise api_error("event_not_found_for_organisation", status.HTTP_404_NOT_FOUND)

    ev_status = (event.status or "config").lower()
    if ev_status not in ORDER_ACCEPT_STATUSES:
        raise api_error("event_status_does_not_accept_payments", status.HTTP_403_FORBIDDEN, status=ev_status)

    if SUMUP_CONNECTED_PAYMENT_TYPE not in payment_types_from_event(event):
        raise api_error("sumup_connected_not_enabled", status.HTTP_403_FORBIDDEN)

    organisation = event.organisation
    if not organisation or not (organisation.sumup_merchant_code or "").strip():
        raise api_error("sumup_not_connected", status.HTTP_409_CONFLICT)
    if not (organisation.sumup_access_token or organisation.sumup_refresh_token):
        raise api_error("sumup_not_connected", status.HTTP_409_CONFLICT)
    return event, organisation


def _reader_for_org(db: Session, organisation_id: int, reader_id: str) -> SumupReader:
    reader = (
        db.query(SumupReader)
        .filter(
            SumupReader.organisation_id == organisation_id,
            SumupReader.sumup_reader_id == reader_id,
        )
        .first()
    )
    if not reader:
        raise api_error("sumup_reader_not_found", status.HTTP_404_NOT_FOUND)
    return reader


def _checkout_row_for_event(
    db: Session,
    *,
    organisation_id: int,
    event_id: int,
    checkout_id: str,
) -> SumupCheckout:
    row = (
        db.query(SumupCheckout)
        .filter(
            SumupCheckout.organisation_id == organisation_id,
            SumupCheckout.event_id == event_id,
            SumupCheckout.sumup_checkout_id == checkout_id,
        )
        .first()
    )
    if not row:
        raise api_error("sumup_checkout_not_found", status.HTTP_404_NOT_FOUND)
    return row


def _apply_checkout_payload(row: SumupCheckout, payload: dict[str, Any]) -> None:
    apply_checkout_payload(row, payload)


@router.post("/v1/sumup/checkout", response_model=SumupCheckoutRead)
def create_sumup_checkout(
    body: SumupCheckoutCreate,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
) -> SumupCheckoutRead:
    event, organisation = _sumup_organisation_for_event(db, ctx, body.event_id)
    _reader_for_org(db, organisation.id, body.reader_id)
    currency = (body.currency or organisation_currency(organisation, event_currency(event, "CHF"))).upper()
    try:
        access_token = get_valid_access_token(db, organisation)
        created = sumup_client.create_reader_checkout(
            access_token,
            organisation.sumup_merchant_code,
            body.reader_id,
            amount_cents=body.amount_cents,
            currency=currency,
            description=f"Event {event.id}",
            foreign_transaction_id=body.client_order_id,
        )
    except Exception as exc:
        raise sumup_error(exc) from exc

    checkout_id = str(created.get("id") or created.get("checkout_id") or "").strip()
    if not checkout_id:
        raise api_error("sumup_checkout_missing_id", status.HTTP_502_BAD_GATEWAY)

    row = SumupCheckout(
        organisation_id=organisation.id,
        event_id=event.id,
        sumup_reader_id=body.reader_id,
        sumup_checkout_id=checkout_id,
        client_order_id=body.client_order_id,
        amount_cents=body.amount_cents,
        currency=currency,
        status=normalize_checkout_status(str(created.get("status"))),
    )
    _apply_checkout_payload(row, created)
    db.add(row)
    commit_or_raise(db)
    db.refresh(row)
    return SumupCheckoutRead(
        checkout_id=row.sumup_checkout_id,
        status=row.status,
        transaction_id=row.sumup_transaction_id,
    )


@router.post("/v1/sumup/terminate", response_model=SumupTerminateResponse)
def terminate_sumup_checkout(
    body: SumupTerminateBody,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
) -> SumupTerminateResponse:
    _, organisation = _sumup_organisation_for_event(db, ctx, body.event_id)
    _reader_for_org(db, organisation.id, body.reader_id)
    try:
        access_token = get_valid_access_token(db, organisation)
        sumup_client.terminate_checkout(access_token, organisation.sumup_merchant_code, body.reader_id)
    except Exception as exc:
        raise sumup_error(exc) from exc
    return SumupTerminateResponse(ok=True)


@router.get("/v1/sumup/status", response_model=SumupCheckoutRead)
def read_sumup_checkout_status(
    event_id: int = Query(...),
    checkout_id: str = Query(..., min_length=1, max_length=128),
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
) -> SumupCheckoutRead:
    _, organisation = _sumup_organisation_for_event(db, ctx, event_id)
    row = _checkout_row_for_event(
        db,
        organisation_id=organisation.id,
        event_id=event_id,
        checkout_id=checkout_id,
    )
    if row.status in {"paid", "failed", "terminated"}:
        return SumupCheckoutRead(
            checkout_id=row.sumup_checkout_id,
            status=row.status,
            transaction_id=row.sumup_transaction_id,
        )

    try:
        access_token = get_valid_access_token(db, organisation)
        payload = sumup_client.get_checkout(access_token, checkout_id)
    except Exception as exc:
        raise sumup_error(exc) from exc

    _apply_checkout_payload(row, payload)
    commit_or_raise(db)
    db.refresh(row)
    return SumupCheckoutRead(
        checkout_id=row.sumup_checkout_id,
        status=row.status,
        transaction_id=row.sumup_transaction_id,
    )
