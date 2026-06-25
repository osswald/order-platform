"""Event configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..event_config_validation import build_station_article_tree, replace_event_configuration
from ..models import User
from ..schemas.events import EventConfigurationIn, EventConfigurationRead
from ..tenancy import TenantContext, get_current_tenant
from .events_helpers import get_event_for_configuration, serialize_event_configuration

router = APIRouter()


@router.get("/{event_id}/configuration", response_model=EventConfigurationRead)
def read_event_configuration(
    event_id: int,
    fields: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    include_layout_cells = fields != "summary"
    event = get_event_for_configuration(
        db,
        current_user,
        event_id,
        tenant.hire_company_id,
        include_layout_cells=include_layout_cells,
    )
    return serialize_event_configuration(db, event, include_layout_cells=include_layout_cells)


@router.put("/{event_id}/configuration", response_model=EventConfigurationRead)
def put_event_configuration(
    event_id: int,
    body: EventConfigurationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    try:
        replace_event_configuration(
            db,
            event,
            stations_in=body.stations,
            event_waiters_in=body.event_waiters,
            app_layouts_in=body.app_layouts,
            cash_registers_in=body.cash_registers,
            voucher_definitions_in=body.voucher_definitions,
            kitchen_monitors_in=body.kitchen_monitors,
        )
        commit_or_raise(db)
    except HTTPException:
        db.rollback()
        raise
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return serialize_event_configuration(db, event)


@router.get("/{event_id}/station-article-tree")
def read_event_station_article_tree(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    return {"nodes": build_station_article_tree(db, event)}
