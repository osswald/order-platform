from datetime import date, datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ..models import ApplianceLending, Organisation, User
from .auth import get_current_superuser, get_current_user, get_db
from .appliances import _assert_lending_is_planned, _utc_today
from .events import ensure_user_can_use_organisation

router = APIRouter()


class OrganisationBase(BaseModel):
    name: str = Field(..., min_length=1)
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country: str = Field(..., min_length=2)


class OrganisationCreate(OrganisationBase):
    user_ids: List[int] | None = None


class OrganisationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country: str | None = None
    user_ids: List[int] | None = None


class OrganisationRead(OrganisationBase):
    id: int
    user_ids: List[int] = []

    class Config:
        orm_mode = True


class OrgApplianceLendingItem(BaseModel):
    lending_id: int
    appliance_id: int
    appliance_name: str | None
    appliance_type: str
    start_date: date
    end_date: date


class OrganisationApplianceLendingsRead(BaseModel):
    current: List[OrgApplianceLendingItem]
    planned: List[OrgApplianceLendingItem]
    past: List[OrgApplianceLendingItem]


def organisation_response(org: Organisation) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "address": org.address,
        "zip": org.zip,
        "city": org.city,
        "country": org.country,
        "user_ids": [user.id for user in org.users],
    }


@router.get("/", response_model=List[OrganisationRead], dependencies=[Depends(get_current_superuser)])
def read_organisations(db: Session = Depends(get_db)):
    organisations = db.query(Organisation).all()
    return [organisation_response(org) for org in organisations]


@router.get(
    "/{organisation_id}/appliance-lendings",
    response_model=OrganisationApplianceLendingsRead,
)
def read_organisation_appliance_lendings(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id)

    today = datetime.now(timezone.utc).date()
    rows = (
        db.query(ApplianceLending)
        .options(joinedload(ApplianceLending.appliance))
        .filter(ApplianceLending.organisation_id == organisation_id)
        .order_by(ApplianceLending.start_date.desc(), ApplianceLending.id.desc())
        .all()
    )

    current: list[OrgApplianceLendingItem] = []
    planned: list[OrgApplianceLendingItem] = []
    past: list[OrgApplianceLendingItem] = []

    for row in rows:
        appliance = row.appliance
        item = OrgApplianceLendingItem(
            lending_id=row.id,
            appliance_id=row.appliance_id,
            appliance_name=appliance.name if appliance else None,
            appliance_type=appliance.type if appliance else "",
            start_date=row.start_date,
            end_date=row.end_date,
        )
        if row.returned_at is not None:
            past.append(item)
            continue
        if row.end_date < today:
            past.append(item)
            continue
        if row.start_date > today:
            planned.append(item)
            continue
        if row.start_date <= today <= row.end_date:
            current.append(item)
        else:
            past.append(item)

    return OrganisationApplianceLendingsRead(current=current, planned=planned, past=past)


@router.delete(
    "/{organisation_id}/appliance-lendings/{lending_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_organisation_planned_lending(
    organisation_id: int,
    lending_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id)

    lending = (
        db.query(ApplianceLending)
        .filter(
            ApplianceLending.id == lending_id,
            ApplianceLending.organisation_id == organisation_id,
        )
        .first()
    )
    if not lending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lending not found")

    _assert_lending_is_planned(lending, _utc_today())
    db.delete(lending)
    db.commit()
    return None


@router.get("/{organisation_id}", response_model=OrganisationRead, dependencies=[Depends(get_current_superuser)])
def read_organisation(organisation_id: int, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation_response(org)


@router.post("/", response_model=OrganisationRead, dependencies=[Depends(get_current_superuser)])
def create_organisation(org_in: OrganisationCreate, db: Session = Depends(get_db)):
    db_org = Organisation(
        name=org_in.name,
        address=org_in.address,
        zip=org_in.zip,
        city=org_in.city,
        country=org_in.country,
    )
    if org_in.user_ids:
        users = db.query(User).filter(User.id.in_(org_in.user_ids)).all()
        db_org.users = users
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return organisation_response(db_org)


@router.put("/{organisation_id}", response_model=OrganisationRead, dependencies=[Depends(get_current_superuser)])
def update_organisation(organisation_id: int, org_in: OrganisationUpdate, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    if org_in.name is not None:
        org.name = org_in.name
    if org_in.address is not None:
        org.address = org_in.address
    if org_in.zip is not None:
        org.zip = org_in.zip
    if org_in.city is not None:
        org.city = org_in.city
    if org_in.country is not None:
        org.country = org_in.country
    if org_in.user_ids is not None:
        org.users = db.query(User).filter(User.id.in_(org_in.user_ids)).all()
    db.commit()
    db.refresh(org)
    return organisation_response(org)


@router.delete("/{organisation_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_superuser)])
def delete_organisation(organisation_id: int, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    db.delete(org)
    db.commit()
    return {"detail": "Organisation deleted"}
