"""Cloud-hosted Pi sandboxes for config-status events."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..deps import get_db
from ..hosted_pi_service import (
    _active_instance_for_event,
    create_hosted_pi,
    instance_to_read,
    stop_hosted_pi,
)
from ..models import HostedPiInstance, User
from ..routers.events import get_event_for_configuration
from ..tenancy import TenantContext, get_current_tenant

router = APIRouter()


class HostedPiRead(BaseModel):
    id: int
    event_id: int
    status: str
    url: str | None = None
    expires_at: datetime
    created_at: datetime | None = None
    stopped_at: datetime | None = None
    last_error: str | None = None


def _latest_instance(db: Session, event_id: int) -> HostedPiInstance | None:
    row = _active_instance_for_event(db, event_id)
    if row:
        return row
    return (
        db.query(HostedPiInstance)
        .filter(HostedPiInstance.event_id == event_id)
        .order_by(HostedPiInstance.id.desc())
        .first()
    )


@router.get("/{event_id}/hosted-pi", response_model=HostedPiRead | None)
def get_hosted_pi(
    event_id: int,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    row = _latest_instance(db, event_id)
    if not row:
        return None
    return HostedPiRead(**instance_to_read(row))


@router.post("/{event_id}/hosted-pi", response_model=HostedPiRead, status_code=status.HTTP_201_CREATED)
async def start_hosted_pi(
    event_id: int,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    row = await create_hosted_pi(
        db,
        event=event,
        organisation=event.organisation,
        hire_company_id=tenant.hire_company_id,
        created_by_user_id=current_user.id,
    )
    return HostedPiRead(**instance_to_read(row))


@router.delete("/{event_id}/hosted-pi", response_model=HostedPiRead)
async def delete_hosted_pi(
    event_id: int,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_event_for_configuration(db, current_user, event_id, tenant.hire_company_id)
    row = _active_instance_for_event(db, event_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active hosted Pi for this event")
    row = await stop_hosted_pi(db, row)
    return HostedPiRead(**instance_to_read(row))
