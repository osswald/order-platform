from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Appliance, HireCompany, Organisation, User
from ..tenancy import get_current_platform_admin

router = APIRouter()


class HireCompanyBase(BaseModel):
    name: str = Field(..., min_length=1)
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country: str | None = None


class HireCompanyCreate(HireCompanyBase):
    pass


class HireCompanyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country: str | None = None


class HireCompanyRead(HireCompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


def hire_company_response(company: HireCompany) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "address": company.address,
        "zip": company.zip,
        "city": company.city,
        "country": company.country,
    }


@router.get("/", response_model=List[HireCompanyRead])
def list_hire_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    companies = db.query(HireCompany).order_by(HireCompany.name).all()
    return [hire_company_response(c) for c in companies]


@router.get("/{hire_company_id}", response_model=HireCompanyRead)
def read_hire_company(
    hire_company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verleiher not found")
    return hire_company_response(company)


@router.post("/", response_model=HireCompanyRead, status_code=status.HTTP_201_CREATED)
def create_hire_company(
    company_in: HireCompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    company = HireCompany(
        name=company_in.name,
        address=company_in.address,
        zip=company_in.zip,
        city=company_in.city,
        country=company_in.country,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return hire_company_response(company)


@router.put("/{hire_company_id}", response_model=HireCompanyRead)
def update_hire_company(
    hire_company_id: int,
    company_in: HireCompanyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verleiher not found")
    if company_in.name is not None:
        company.name = company_in.name
    if company_in.address is not None:
        company.address = company_in.address
    if company_in.zip is not None:
        company.zip = company_in.zip
    if company_in.city is not None:
        company.city = company_in.city
    if company_in.country is not None:
        company.country = company_in.country
    db.commit()
    db.refresh(company)
    return hire_company_response(company)


@router.delete("/{hire_company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hire_company(
    hire_company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verleiher not found")
    if (
        db.query(Organisation.id).filter(Organisation.hire_company_id == hire_company_id).first()
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verleiher has organisations and cannot be deleted",
        )
    if db.query(Appliance.id).filter(Appliance.hire_company_id == hire_company_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verleiher has appliances and cannot be deleted",
        )
    db.delete(company)
    db.commit()
    return None
