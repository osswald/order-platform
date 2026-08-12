"""Shared helpers for cloud backend tests."""

from __future__ import annotations

from datetime import date, datetime

from app.models import ApplianceLending, Country, Organisation, Rental
from sqlalchemy.orm import Session


def country_id_by_code(db: Session, code: str = "CH") -> int:
    country = db.query(Country).filter(Country.code == code.upper()).first()
    if not country:
        raise RuntimeError(f"Country with code {code!r} not seeded")
    return country.id


def ensure_country(db: Session, code: str = "CH", *, country_id: int | None = None) -> int:
    existing = db.query(Country).filter(Country.code == code.upper()).first()
    if existing:
        return existing.id
    names = {
        "CH": "Schweiz",
        "DE": "Deutschland",
        "AT": "Österreich",
        "FR": "Frankreich",
        "IT": "Italien",
        "BE": "Belgien",
        "NL": "Niederlande",
    }
    country = Country(
        id=country_id,
        code=code.upper(),
        name=names.get(code.upper(), code.upper()),
    )
    db.add(country)
    db.flush()
    return country.id


def add_lending(
    db: Session,
    *,
    appliance_id: int,
    organisation_id: int,
    start_date: date,
    end_date: date,
    returned_at: datetime | None = None,
    hire_company_id: int | None = None,
    label: str | None = None,
) -> ApplianceLending:
    """Create a rental container plus one appliance lending (required FK)."""
    if hire_company_id is None:
        org = db.get(Organisation, organisation_id)
        if org is None:
            raise RuntimeError(f"Organisation {organisation_id} not found")
        hire_company_id = org.hire_company_id
    rental = Rental(
        hire_company_id=hire_company_id,
        organisation_id=organisation_id,
        start_date=start_date,
        end_date=end_date,
        label=label,
    )
    db.add(rental)
    db.flush()
    lending = ApplianceLending(
        rental_id=rental.id,
        appliance_id=appliance_id,
        organisation_id=organisation_id,
        start_date=start_date,
        end_date=end_date,
        returned_at=returned_at,
    )
    db.add(lending)
    return lending
