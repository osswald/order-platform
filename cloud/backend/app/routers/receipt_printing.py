"""Receipt printing configuration and logo upload endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from ..i18n.errors import api_error
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..deps import get_db
from ..db_errors import commit_or_raise
from ..models import Event, HireCompany, Organisation, User
from ..receipt_printing_config import (
    EventReceiptPrintingUpdate,
    ReceiptPrintingConfigUpdate,
    ReceiptPrintingRead,
    apply_event_printing_update,
    apply_vendor_or_org_printing_update,
    clear_receipt_logo,
    read_printing_response,
    receipt_logo_bytes,
    store_receipt_logo,
)
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    get_current_tenant,
    get_current_tenant_admin,
)
from ..user_access import is_platform_admin

router = APIRouter()


def _ensure_hire_company_access(
    db: Session,
    hire_company_id: int,
    user: User,
    tenant: TenantContext | None,
) -> HireCompany:
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise api_error("verleiher_not_found", status.HTTP_404_NOT_FOUND)
    if is_platform_admin(user):
        return company
    if tenant is None or tenant.hire_company_id != hire_company_id:
        raise api_error("not_allowed_for_verleiher", status.HTTP_403_FORBIDDEN)
    return company


@router.get("/hire-companies/{hire_company_id}/receipt-printing", response_model=ReceiptPrintingRead)
def get_hire_company_receipt_printing(
    hire_company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    company = _ensure_hire_company_access(db, hire_company_id, current_user, tenant)
    return read_printing_response(company, is_event=False)


@router.put("/hire-companies/{hire_company_id}/receipt-printing", response_model=ReceiptPrintingRead)
def put_hire_company_receipt_printing(
    hire_company_id: int,
    body: ReceiptPrintingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    company = _ensure_hire_company_access(db, hire_company_id, current_user, tenant)
    apply_vendor_or_org_printing_update(company, body)
    commit_or_raise(db)
    db.refresh(company)
    return read_printing_response(company, is_event=False)


@router.get("/hire-companies/{hire_company_id}/receipt-logo")
def get_hire_company_receipt_logo(
    hire_company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    company = _ensure_hire_company_access(db, hire_company_id, current_user, tenant)
    payload = receipt_logo_bytes(company)
    if not payload:
        raise api_error("no_receipt_logo", status.HTTP_404_NOT_FOUND)
    mime, raw = payload
    return Response(content=raw, media_type=mime)


@router.put("/hire-companies/{hire_company_id}/receipt-logo")
async def put_hire_company_receipt_logo(
    hire_company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    company = _ensure_hire_company_access(db, hire_company_id, current_user, tenant)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        store_receipt_logo(company, mime, raw)
    except ValueError as e:
        raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST) from e
    commit_or_raise(db)
    return {"ok": True, "has_receipt_logo": True}


@router.delete("/hire-companies/{hire_company_id}/receipt-logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_hire_company_receipt_logo(
    hire_company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    company = _ensure_hire_company_access(db, hire_company_id, current_user, tenant)
    clear_receipt_logo(company)
    commit_or_raise(db)


@router.get("/organisations/{organisation_id}/receipt-printing", response_model=ReceiptPrintingRead)
def get_organisation_receipt_printing(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    return read_printing_response(org, is_event=False)


@router.put("/organisations/{organisation_id}/receipt-printing", response_model=ReceiptPrintingRead)
def put_organisation_receipt_printing(
    organisation_id: int,
    body: ReceiptPrintingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    apply_vendor_or_org_printing_update(org, body)
    commit_or_raise(db)
    db.refresh(org)
    return read_printing_response(org, is_event=False)


@router.get("/organisations/{organisation_id}/receipt-logo")
def get_organisation_receipt_logo(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    payload = receipt_logo_bytes(org)
    if not payload:
        raise api_error("no_receipt_logo", status.HTTP_404_NOT_FOUND)
    mime, raw = payload
    return Response(content=raw, media_type=mime)


@router.put("/organisations/{organisation_id}/receipt-logo")
async def put_organisation_receipt_logo(
    organisation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        store_receipt_logo(org, mime, raw)
    except ValueError as e:
        raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST) from e
    commit_or_raise(db)
    return {"ok": True, "has_receipt_logo": True}


@router.delete("/organisations/{organisation_id}/receipt-logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_organisation_receipt_logo(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    clear_receipt_logo(org)
    commit_or_raise(db)


def _get_event_for_printing(db, current_user, event_id, hire_company_id) -> Event:
    from .events import get_event_for_configuration

    return get_event_for_configuration(db, current_user, event_id, hire_company_id)


@router.get("/events/{event_id}/receipt-printing", response_model=ReceiptPrintingRead)
def get_event_receipt_printing(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = _get_event_for_printing(db, current_user, event_id, tenant.hire_company_id)
    return read_printing_response(event, is_event=True)


@router.put("/events/{event_id}/receipt-printing", response_model=ReceiptPrintingRead)
def put_event_receipt_printing(
    event_id: int,
    body: EventReceiptPrintingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = _get_event_for_printing(db, current_user, event_id, tenant.hire_company_id)
    apply_event_printing_update(event, body)
    commit_or_raise(db)
    db.refresh(event)
    return read_printing_response(event, is_event=True)


@router.get("/events/{event_id}/receipt-logo")
def get_event_receipt_logo(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = _get_event_for_printing(db, current_user, event_id, tenant.hire_company_id)
    payload = receipt_logo_bytes(event)
    if not payload:
        raise api_error("no_receipt_logo", status.HTTP_404_NOT_FOUND)
    mime, raw = payload
    return Response(content=raw, media_type=mime)


@router.put("/events/{event_id}/receipt-logo")
async def put_event_receipt_logo(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = _get_event_for_printing(db, current_user, event_id, tenant.hire_company_id)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        store_receipt_logo(event, mime, raw)
    except ValueError as e:
        raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST) from e
    commit_or_raise(db)
    return {"ok": True, "has_receipt_logo": True}


@router.delete("/events/{event_id}/receipt-logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_receipt_logo(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = _get_event_for_printing(db, current_user, event_id, tenant.hire_company_id)
    clear_receipt_logo(event)
    commit_or_raise(db)
