from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..auth_deps import get_current_user
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import TaxCode, TaxCodeRate, User
from ..reference_countries import assert_tax_code_deletable, country_response, get_country_or_404
from ..tenancy import get_current_platform_admin

router = APIRouter()


class TaxCodeRateBase(BaseModel):
    rate_percent: float = Field(..., ge=0)
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        return self


class TaxCodeRateRead(TaxCodeRateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CountryNestedRead(BaseModel):
    id: int
    code: str
    name: str


class TaxCodeRead(BaseModel):
    id: int
    country_id: int
    name: str
    country: CountryNestedRead
    rates: List[TaxCodeRateRead]


class TaxCodeCreate(BaseModel):
    country_id: int
    name: str = Field(..., min_length=1)
    rates: List[TaxCodeRateBase] = Field(..., min_length=1)


class TaxCodeUpdate(BaseModel):
    country_id: int | None = None
    name: str | None = Field(None, min_length=1)
    rates: List[TaxCodeRateBase] | None = None


def _rate_response(rate: TaxCodeRate) -> dict:
    return {
        "id": rate.id,
        "rate_percent": rate.rate_percent,
        "valid_from": rate.valid_from,
        "valid_to": rate.valid_to,
    }


def _tax_code_response(tax_code: TaxCode) -> dict:
    return {
        "id": tax_code.id,
        "country_id": tax_code.country_id,
        "name": tax_code.name,
        "country": country_response(tax_code.country),
        "rates": [_rate_response(rate) for rate in tax_code.rates],
    }


def _periods_overlap(
    start_a: date,
    end_a: date | None,
    start_b: date,
    end_b: date | None,
) -> bool:
    end_a_eff = end_a if end_a is not None else date.max
    end_b_eff = end_b if end_b is not None else date.max
    return start_a <= end_b_eff and start_b <= end_a_eff


def _assert_no_rate_overlaps(rates: List[TaxCodeRateBase]) -> None:
    for index, rate in enumerate(rates):
        for other in rates[index + 1 :]:
            if _periods_overlap(rate.valid_from, rate.valid_to, other.valid_from, other.valid_to):
                raise api_error("tax_code_overlap", status.HTTP_400_BAD_REQUEST)


def _apply_rates(tax_code: TaxCode, rates: List[TaxCodeRateBase]) -> None:
    _assert_no_rate_overlaps(rates)
    tax_code.rates.clear()
    for rate in rates:
        tax_code.rates.append(
            TaxCodeRate(
                rate_percent=rate.rate_percent,
                valid_from=rate.valid_from,
                valid_to=rate.valid_to,
            )
        )


def _get_tax_code_or_404(db: Session, tax_code_id: int) -> TaxCode:
    tax_code = (
        db.query(TaxCode)
        .options(joinedload(TaxCode.country), joinedload(TaxCode.rates))
        .filter(TaxCode.id == tax_code_id)
        .first()
    )
    if not tax_code:
        raise api_error("tax_code_not_found", status.HTTP_404_NOT_FOUND)
    return tax_code


@router.get("/", response_model=List[TaxCodeRead])
def list_tax_codes(
    country_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = (
        db.query(TaxCode)
        .options(joinedload(TaxCode.country), joinedload(TaxCode.rates))
        .order_by(TaxCode.country_id, TaxCode.name)
    )
    if country_id is not None:
        query = query.filter(TaxCode.country_id == country_id)
    tax_codes = query.all()
    return [_tax_code_response(tax_code) for tax_code in tax_codes]


@router.get("/{tax_code_id}", response_model=TaxCodeRead)
def read_tax_code(
    tax_code_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _tax_code_response(_get_tax_code_or_404(db, tax_code_id))


@router.post("/", response_model=TaxCodeRead, status_code=status.HTTP_201_CREATED)
def create_tax_code(
    body: TaxCodeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    get_country_or_404(db, body.country_id)
    tax_code = TaxCode(country_id=body.country_id, name=body.name.strip())
    _apply_rates(tax_code, body.rates)
    db.add(tax_code)
    db.commit()
    db.refresh(tax_code)
    tax_code = _get_tax_code_or_404(db, tax_code.id)
    return _tax_code_response(tax_code)


@router.put("/{tax_code_id}", response_model=TaxCodeRead)
def update_tax_code(
    tax_code_id: int,
    body: TaxCodeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    tax_code = _get_tax_code_or_404(db, tax_code_id)
    if body.country_id is not None:
        get_country_or_404(db, body.country_id)
        tax_code.country_id = body.country_id
    if body.name is not None:
        tax_code.name = body.name.strip()
    if body.rates is not None:
        _apply_rates(tax_code, body.rates)
    db.commit()
    tax_code = _get_tax_code_or_404(db, tax_code_id)
    return _tax_code_response(tax_code)


@router.delete("/{tax_code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax_code(
    tax_code_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    tax_code = _get_tax_code_or_404(db, tax_code_id)
    assert_tax_code_deletable(db, tax_code_id)
    db.delete(tax_code)
    db.commit()
    return None
