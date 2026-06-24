from typing import List

from fastapi import APIRouter, Depends, status
from ..i18n.errors import api_error
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..auth_deps import get_current_user
from ..deps import get_db
from ..db_errors import commit_or_raise
from ..models import Appliance, HireCompany, Organisation, User
from ..reference_countries import country_response, get_country_or_404
from ..tenancy import ensure_can_access_hire_company, get_current_platform_admin

router = APIRouter()


class CountryRead(BaseModel):
    id: int
    code: str
    name: str


class HireCompanyBase(BaseModel):
    name: str = Field(..., min_length=1)
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country_id: int | None = None


class HireCompanyCreate(HireCompanyBase):
    pass


class HireCompanyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country_id: int | None = None


class HireCompanyRead(HireCompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country: CountryRead | None = None


def hire_company_response(company: HireCompany) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "address": company.address,
        "zip": company.zip,
        "city": company.city,
        "country_id": company.country_id,
        "country": country_response(company.country) if company.country else None,
    }


def _load_hire_company(db: Session, hire_company_id: int) -> HireCompany | None:
    return (
        db.query(HireCompany)
        .options(joinedload(HireCompany.country))
        .filter(HireCompany.id == hire_company_id)
        .first()
    )


@router.get("/", response_model=List[HireCompanyRead])
def list_hire_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    companies = (
        db.query(HireCompany)
        .options(joinedload(HireCompany.country))
        .order_by(HireCompany.name)
        .all()
    )
    return [hire_company_response(c) for c in companies]


@router.get("/{hire_company_id}", response_model=HireCompanyRead)
def read_hire_company(
    hire_company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_can_access_hire_company(current_user, hire_company_id)
    company = _load_hire_company(db, hire_company_id)
    if not company:
        raise api_error("verleiher_not_found", status.HTTP_404_NOT_FOUND)
    return hire_company_response(company)


@router.post("/", response_model=HireCompanyRead, status_code=status.HTTP_201_CREATED)
def create_hire_company(
    company_in: HireCompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    if company_in.country_id is not None:
        get_country_or_404(db, company_in.country_id)
    company = HireCompany(
        name=company_in.name,
        address=company_in.address,
        zip=company_in.zip,
        city=company_in.city,
        country_id=company_in.country_id,
    )
    db.add(company)
    commit_or_raise(db)
    company = _load_hire_company(db, company.id)
    return hire_company_response(company)


@router.put("/{hire_company_id}", response_model=HireCompanyRead)
def update_hire_company(
    hire_company_id: int,
    company_in: HireCompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_can_access_hire_company(current_user, hire_company_id)
    company = _load_hire_company(db, hire_company_id)
    if not company:
        raise api_error("verleiher_not_found", status.HTTP_404_NOT_FOUND)
    if company_in.name is not None:
        company.name = company_in.name
    if company_in.address is not None:
        company.address = company_in.address
    if company_in.zip is not None:
        company.zip = company_in.zip
    if company_in.city is not None:
        company.city = company_in.city
    if company_in.country_id is not None:
        get_country_or_404(db, company_in.country_id)
        company.country_id = company_in.country_id
    commit_or_raise(db)
    company = _load_hire_company(db, hire_company_id)
    return hire_company_response(company)


@router.delete("/{hire_company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hire_company(
    hire_company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise api_error("verleiher_not_found", status.HTTP_404_NOT_FOUND)
    if (
        db.query(Organisation.id).filter(Organisation.hire_company_id == hire_company_id).first()
        is not None
    ):
        raise api_error("verleiher_has_organisations", status.HTTP_400_BAD_REQUEST)
    if db.query(Appliance.id).filter(Appliance.hire_company_id == hire_company_id).first() is not None:
        raise api_error("verleiher_has_appliances", status.HTTP_400_BAD_REQUEST)
    db.delete(company)
    commit_or_raise(db)
    return None
