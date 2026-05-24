from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..models import Organisation, User, Waiter
from .auth import get_current_user
from ..deps import get_db

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


def readable_waiters_query(db: Session, current_user: User):
    query = db.query(Waiter).options(joinedload(Waiter.organisation))
    if current_user.is_superuser:
        return query
    return (
        query.join(Waiter.organisation)
        .join(Organisation.users)
        .filter(User.id == current_user.id)
    )


def readable_organisations(db: Session, current_user: User) -> list[Organisation]:
    if current_user.is_superuser:
        return db.query(Organisation).order_by(Organisation.name).all()
    return sorted(current_user.organisations or [], key=lambda org: org.name.lower())


def ensure_organisation_exists(db: Session, organisation_id: int) -> Organisation:
    organisation = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not organisation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation


def ensure_user_can_use_organisation(
    db: Session,
    current_user: User,
    organisation_id: int | None,
) -> Organisation:
    organisations = readable_organisations(db, current_user)
    if organisation_id is None:
        if len(organisations) == 1:
            return organisations[0]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organisation is required when the user is linked to multiple organisations",
        )
    organisation = ensure_organisation_exists(db, organisation_id)
    if current_user.is_superuser:
        return organisation
    if not any(org.id == organisation.id for org in organisations):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this organisation")
    return organisation


@router.get("/", response_model=List[WaiterRead])
def read_waiters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    waiters = readable_waiters_query(db, current_user).order_by(Waiter.name).all()
    return [waiter_response(waiter) for waiter in waiters]


@router.get("/{waiter_id}", response_model=WaiterRead)
def read_waiter(
    waiter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    waiter = readable_waiters_query(db, current_user).filter(Waiter.id == waiter_id).first()
    if not waiter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waiter not found")
    return waiter_response(waiter)


@router.post("/", response_model=WaiterRead)
def create_waiter(
    waiter_in: WaiterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organisation = ensure_user_can_use_organisation(db, current_user, waiter_in.organisation_id)
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
):
    waiter = readable_waiters_query(db, current_user).filter(Waiter.id == waiter_id).first()
    if not waiter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waiter not found")

    if waiter_in.organisation_id is not None:
        organisation = ensure_user_can_use_organisation(db, current_user, waiter_in.organisation_id)
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
):
    waiter = readable_waiters_query(db, current_user).filter(Waiter.id == waiter_id).first()
    if not waiter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waiter not found")
    db.delete(waiter)
    db.commit()
    return None
