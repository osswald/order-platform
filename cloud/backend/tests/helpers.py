"""Shared helpers for cloud backend tests."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Country


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
