from typing import List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import Country, User
from ..reference_countries import assert_country_deletable, country_response, get_country_or_404
from ..tenancy import get_current_platform_admin

router = APIRouter()


def _raise_country_code_taken() -> None:
    raise api_error("country_code_taken", status.HTTP_400_BAD_REQUEST)


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class CountryCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=2)
    name: str = Field(..., min_length=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CountryUpdate(BaseModel):
    code: str | None = Field(None, min_length=2, max_length=2)
    name: str | None = Field(None, min_length=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


@router.get("/", response_model=List[CountryRead])
def list_countries(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    countries = db.query(Country).order_by(Country.name).all()
    return [country_response(c) for c in countries]


@router.get("/{country_id}", response_model=CountryRead)
def read_country(
    country_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return country_response(get_country_or_404(db, country_id))


@router.post("/", response_model=CountryRead, status_code=status.HTTP_201_CREATED)
def create_country(
    body: CountryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    country = Country(code=body.code, name=body.name.strip())
    db.add(country)

    def on_integrity() -> None:
        existing = db.query(Country).filter(
            (Country.code == body.code) | (Country.name == body.name.strip())
        ).first()
        if existing and existing.code == body.code:
            raise api_error("country_code_taken", status.HTTP_400_BAD_REQUEST) from None
        raise api_error("country_name_taken", status.HTTP_400_BAD_REQUEST) from None

    commit_or_raise(db, on_integrity=on_integrity)
    db.refresh(country)
    return country_response(country)


@router.put("/{country_id}", response_model=CountryRead)
def update_country(
    country_id: int,
    body: CountryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    country = get_country_or_404(db, country_id)
    if body.code is not None:
        country.code = body.code
    if body.name is not None:
        country.name = body.name.strip()
    commit_or_raise(db, on_integrity=_raise_country_code_taken)
    db.refresh(country)
    return country_response(country)


@router.delete("/{country_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_country(
    country_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    country = get_country_or_404(db, country_id)
    assert_country_deletable(db, country_id)
    db.delete(country)
    commit_or_raise(db)
    return None
