"""Event reporting routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..deps import get_db
from ..edge_reporting import build_payment_batches_report_v3, build_sales_report_v3
from ..event_bookkeeping import build_event_bookkeeping_report
from ..event_cash_sessions import build_cash_sessions_page
from ..event_collective_bills import build_event_collective_bills_list
from ..event_sales import build_event_sales_report
from ..event_transactions import build_event_transactions_page
from ..i18n.errors import api_error
from ..models import User
from ..schemas.events import (
    EventCashSessionsPageRead,
    EventCollectiveBillsListRead,
    EventPaymentBatchesV3Read,
    EventSalesReportRead,
    EventSalesReportV3Read,
    EventTransactionsPageRead,
)
from ..tenancy import TenantContext, get_current_tenant
from .events_helpers import get_event_for_configuration

router = APIRouter()


@router.get("/{event_id}/sales-report", response_model=EventSalesReportRead)
def read_event_sales_report(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_event_sales_report(db, event)


@router.get("/{event_id}/collective-bills", response_model=EventCollectiveBillsListRead)
def read_event_collective_bills(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_event_collective_bills_list(db, event)


@router.get("/{event_id}/transactions", response_model=EventTransactionsPageRead)
def read_event_transactions(
    event_id: int,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(25, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_desc: bool = Query(True),
    payment_status: str | None = Query(None),
    kind: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_event_transactions_page(
        db,
        event,
        page=page,
        items_per_page=items_per_page,
        sort_by=sort_by,
        sort_desc=sort_desc,
        payment_status=payment_status,
        kind=kind,
    )


@router.get("/{event_id}/cash-sessions", response_model=EventCashSessionsPageRead)
def read_event_cash_sessions(
    event_id: int,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(25, ge=1, le=200),
    sort_by: str = Query("started_at"),
    sort_desc: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_cash_sessions_page(
        db,
        event,
        page=page,
        items_per_page=items_per_page,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


@router.get("/{event_id}/sales-report-v3", response_model=EventSalesReportV3Read)
def read_event_sales_report_v3(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_sales_report_v3(db, organisation_id=event.organisation_id, event_id=event.id)


@router.get("/{event_id}/payment-batches-v3", response_model=EventPaymentBatchesV3Read)
def read_event_payment_batches_v3(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return build_payment_batches_report_v3(db, organisation_id=event.organisation_id, event_id=event.id)


@router.get("/{event_id}/bookkeeping")
def read_event_bookkeeping(
    event_id: int,
    view: str = Query("both", pattern="^(summary|detail|both)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    result = build_event_bookkeeping_report(
        db,
        organisation_id=event.organisation_id,
        event_id=event.id,
        view=view,
    )
    if result.get("error") == "event_not_found":
        raise api_error("event_not_found", status.HTTP_404_NOT_FOUND)
    if result.get("error") == "accounts_not_enabled":
        raise api_error("accounts_not_enabled", status.HTTP_409_CONFLICT)
    return result
