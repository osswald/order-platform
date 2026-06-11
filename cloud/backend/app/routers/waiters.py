from typing import List

from fastapi import APIRouter, Depends, Query, status
from ..i18n.errors import api_error
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..models import Organisation, User, Waiter
from ..auth_deps import get_current_user
from ..deps import get_db
from ..tenancy import (
    TenantContext,
    ensure_user_can_use_organisation,
    get_current_tenant,
)
from ..user_access import can_manage_tenant

router = APIRouter()


class WaiterBase(BaseModel):
    name: str = Field(..., min_length=1)
    pin: str = Field("0000", min_length=1, max_length=32)
    organisation_id: int


class WaiterCreate(BaseModel):
    name: str = Field(..., min_length=1)
    pin: str = Field("0000", min_length=1, max_length=32)
    organisation_id: int | None = None


class WaiterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    pin: str | None = Field(None, min_length=1, max_length=32)
    organisation_id: int | None = None


class WaiterRead(WaiterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_name: str


def waiter_response(waiter: Waiter) -> dict:
    return {
        "id": waiter.id,
        "name": waiter.name,
        "pin": waiter.pin,
        "organisation_id": waiter.organisation_id,
        "organisation_name": waiter.organisation.name if waiter.organisation else "",
    }


def readable_waiters_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(Waiter)
        .options(joinedload(Waiter.organisation))
        .join(Waiter.organisation)
        .filter(Organisation.hire_company_id == hire_company_id)
    )
    if can_manage_tenant(current_user):
        return query
    return query.join(Organisation.users).filter(User.id == current_user.id)


@router.get("/", response_model=List[WaiterRead])
def read_waiters(
    organisation_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    query = readable_waiters_query(db, current_user, tenant.hire_company_id)
    if organisation_id is not None:
        query = query.filter(Waiter.organisation_id == organisation_id)
    waiters = query.order_by(Waiter.name).all()
    return [waiter_response(waiter) for waiter in waiters]


@router.get("/{waiter_id}", response_model=WaiterRead)
def read_waiter(
    waiter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    waiter = (
        readable_waiters_query(db, current_user, tenant.hire_company_id)
        .filter(Waiter.id == waiter_id)
        .first()
    )
    if not waiter:
        raise api_error("waiter_not_found", status.HTTP_404_NOT_FOUND)
    return waiter_response(waiter)


@router.post("/", response_model=WaiterRead)
def create_waiter(
    waiter_in: WaiterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    organisation = ensure_user_can_use_organisation(
        db, current_user, waiter_in.organisation_id, tenant.hire_company_id
    )
    waiter = Waiter(
        name=waiter_in.name,
        pin=waiter_in.pin or "0000",
        organisation_id=organisation.id,
    )
    db.add(waiter)
    db.commit()
    db.refresh(waiter)
    return waiter_response(waiter)


@router.put("/{waiter_id}", response_model=WaiterRead)
def update_waiter(
    waiter_id: int,
    waiter_in: WaiterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    waiter = (
        readable_waiters_query(db, current_user, tenant.hire_company_id)
        .filter(Waiter.id == waiter_id)
        .first()
    )
    if not waiter:
        raise api_error("waiter_not_found", status.HTTP_404_NOT_FOUND)

    if waiter_in.organisation_id is not None:
        organisation = ensure_user_can_use_organisation(
            db, current_user, waiter_in.organisation_id, tenant.hire_company_id
        )
        waiter.organisation_id = organisation.id
    if waiter_in.name is not None:
        waiter.name = waiter_in.name
    if waiter_in.pin is not None:
        waiter.pin = waiter_in.pin or "0000"

    db.commit()
    db.refresh(waiter)
    return waiter_response(waiter)


@router.delete("/{waiter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_waiter(
    waiter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    waiter = (
        readable_waiters_query(db, current_user, tenant.hire_company_id)
        .filter(Waiter.id == waiter_id)
        .first()
    )
    if not waiter:
        raise api_error("waiter_not_found", status.HTTP_404_NOT_FOUND)
    db.delete(waiter)
    db.commit()
    return None
