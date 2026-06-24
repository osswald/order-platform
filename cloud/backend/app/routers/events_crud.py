"""Event CRUD routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..event_copy import copy_event, default_copy_name
from ..event_status import ALLOWED_STATUSES, assert_create_status, purge_event_operational_data, validate_status_transition
from ..i18n.errors import api_error
from ..instant_collective_bill import apply_instant_collective_bill_settings
from ..models import Event, User
from ..payment_types_config import normalize_payment_types
from ..schemas.events import PAYMENT_MODES, EventCopyIn, EventCreate, EventRead, EventUpdate
from ..tenancy import (
    TenantContext,
    ensure_user_can_use_organisation,
    get_current_tenant,
    get_current_tenant_admin,
    readable_events_query,
    readable_organisations,
)
from ..twint_qr import clear_twint_qr
from .events_helpers import event_response, get_event_for_configuration

router = APIRouter()


@router.get("/", response_model=List[EventRead])
def read_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    events = readable_events_query(db, current_user, tenant.hire_company_id).order_by(Event.start.desc()).all()
    return [event_response(event) for event in events]


@router.get("/organisations")
def read_event_organisations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return [
        {
            "id": org.id,
            "name": org.name,
            "currency": org.currency,
            "country_id": org.country_id,
            "vat_liable": bool(org.vat_liable),
            "default_tax_code_id": org.default_tax_code_id,
            "accounts_enabled": bool(org.accounts_enabled),
        }
        for org in readable_organisations(db, current_user, tenant.hire_company_id)
    ]


@router.get("/{event_id}", response_model=EventRead)
def read_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = readable_events_query(db, current_user, tenant.hire_company_id).filter(Event.id == event_id).first()
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    return event_response(event)


@router.post("/", response_model=EventRead)
def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    organisation = ensure_user_can_use_organisation(db, current_user, event_in.organisation_id, tenant.hire_company_id)
    create_status = assert_create_status(event_in.status)
    event = Event(
        name=event_in.name,
        status=create_status,
        start=event_in.start,
        end=event_in.end,
        organisation_id=organisation.id,
        payment_mode=event_in.payment_mode,
        payment_types=event_in.payment_types,
        cash_registers_enabled=bool(event_in.cash_registers_enabled),
        shift_settlement_enabled=bool(event_in.shift_settlement_enabled),
        vouchers_enabled=bool(event_in.vouchers_enabled),
        discounts_enabled=bool(event_in.discounts_enabled),
        alternative_printers_enabled=bool(event_in.alternative_printers_enabled),
        kitchen_monitors_enabled=bool(event_in.kitchen_monitors_enabled),
        offer_payment_receipt=bool(event_in.offer_payment_receipt),
    )
    apply_instant_collective_bill_settings(
        event,
        payment_mode=event_in.payment_mode,
        instant_collective_bill_name=event_in.instant_collective_bill_name,
        payment_mode_set=True,
        instant_collective_bill_name_set=True,
    )
    db.add(event)
    db.flush()
    from ..receipt_printing_config import copy_receipt_printing_from_organisation

    copy_receipt_printing_from_organisation(organisation, event)
    commit_or_raise(db)
    db.refresh(event)
    return event_response(event)


@router.post("/{event_id}/copy", response_model=EventRead)
def copy_event_endpoint(
    event_id: int,
    body: EventCopyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    source = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    copy_name = (body.name or "").strip() or default_copy_name(source.name)
    try:
        new_event = copy_event(db, source, name=copy_name)
        commit_or_raise(db)
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT) from e
    new_event = get_event_for_configuration(db, current_user, new_event.id, tenant.hire_company_id)
    return event_response(new_event)


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = readable_events_query(db, current_user, tenant.hire_company_id).filter(Event.id == event_id).first()
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)

    if event_in.organisation_id is not None:
        organisation = ensure_user_can_use_organisation(db, current_user, event_in.organisation_id, tenant.hire_company_id)
        event.organisation_id = organisation.id
    if event_in.name is not None:
        event.name = event_in.name
    if event_in.status is not None:
        status_value = event_in.status.lower()
        if status_value not in ALLOWED_STATUSES:
            raise api_error("status_must_be_one_of", status.HTTP_422_UNPROCESSABLE_CONTENT, statuses=", ".join(sorted(ALLOWED_STATUSES)))
        old_status = event.status
        validate_status_transition(old_status, status_value)
        if old_status == "test" and status_value == "prod":
            purge_event_operational_data(db, event)
        event.status = status_value
    if event_in.start is not None:
        event.start = event_in.start
    if event_in.end is not None:
        event.end = event_in.end
    if event_in.payment_mode is not None:
        pm = event_in.payment_mode.lower()
        if pm not in PAYMENT_MODES:
            raise api_error("payment_mode_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT, modes=", ".join(sorted(PAYMENT_MODES)))
        event.payment_mode = pm
    if event_in.instant_collective_bill_name is not None:
        event.instant_collective_bill_name = event_in.instant_collective_bill_name
    apply_instant_collective_bill_settings(
        event,
        payment_mode=event.payment_mode,
        instant_collective_bill_name=event.instant_collective_bill_name,
        payment_mode_set=event_in.payment_mode is not None,
        instant_collective_bill_name_set=event_in.instant_collective_bill_name is not None,
    )
    if event_in.payment_types is not None:
        try:
            new_types = normalize_payment_types(event_in.payment_types)
            event.payment_types = new_types
            if "twint" not in new_types:
                clear_twint_qr(event)
        except ValueError as e:
            raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT) from e
    if event_in.cash_registers_enabled is not None:
        event.cash_registers_enabled = bool(event_in.cash_registers_enabled)
    if event_in.shift_settlement_enabled is not None:
        event.shift_settlement_enabled = bool(event_in.shift_settlement_enabled)
    if event_in.vouchers_enabled is not None:
        event.vouchers_enabled = bool(event_in.vouchers_enabled)
    if event_in.discounts_enabled is not None:
        event.discounts_enabled = bool(event_in.discounts_enabled)
    if event_in.alternative_printers_enabled is not None:
        event.alternative_printers_enabled = bool(event_in.alternative_printers_enabled)
    if event_in.kitchen_monitors_enabled is not None:
        event.kitchen_monitors_enabled = bool(event_in.kitchen_monitors_enabled)
    if event_in.offer_payment_receipt is not None:
        event.offer_payment_receipt = bool(event_in.offer_payment_receipt)
    if event.end < event.start:
        raise api_error("end_must_be_after_start", status.HTTP_422_UNPROCESSABLE_CONTENT)

    commit_or_raise(db)
    db.refresh(event)
    return event_response(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    event = (
        readable_events_query(db, current_user, tenant.hire_company_id)
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    db.delete(event)
    commit_or_raise(db)
    return None
