"""Shared helpers for country reference data."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from .i18n.errors import api_error
from .models import Article, Country, HireCompany, Organisation, TaxCode

SEEDED_COUNTRIES: list[tuple[str, str]] = [
    ("DE", "Deutschland"),
    ("AT", "Österreich"),
    ("CH", "Schweiz"),
    ("FR", "Frankreich"),
    ("IT", "Italien"),
    ("BE", "Belgien"),
    ("NL", "Niederlande"),
]

_LEGACY_COUNTRY_ALIASES: dict[str, str] = {
    "de": "DE",
    "deutschland": "DE",
    "at": "AT",
    "österreich": "AT",
    "austria": "AT",
    "ch": "CH",
    "schweiz": "CH",
    "switzerland": "CH",
    "fr": "FR",
    "frankreich": "FR",
    "france": "FR",
    "it": "IT",
    "italien": "IT",
    "italy": "IT",
    "be": "BE",
    "belgien": "BE",
    "belgium": "BE",
    "nl": "NL",
    "niederlande": "NL",
    "netherlands": "NL",
}


def country_response(country: Country) -> dict:
    return {"id": country.id, "code": country.code, "name": country.name}


def resolve_legacy_country_code(value: str | None, *, default_code: str | None = "CH") -> str | None:
    if value is None or not str(value).strip():
        return default_code
    normalized = str(value).strip()
    if len(normalized) == 2:
        return normalized.upper()
    alias = _LEGACY_COUNTRY_ALIASES.get(normalized.lower())
    if alias:
        return alias
    for code, name in SEEDED_COUNTRIES:
        if normalized.lower() == name.lower():
            return code
    return default_code


def get_country_or_404(db: Session, country_id: int) -> Country:
    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        raise api_error("country_not_found", status.HTTP_404_NOT_FOUND)
    return country


def assert_country_deletable(db: Session, country_id: int) -> None:
    if db.query(Organisation.id).filter(Organisation.country_id == country_id).first() is not None:
        raise api_error("country_in_use", status.HTTP_400_BAD_REQUEST)
    if db.query(HireCompany.id).filter(HireCompany.country_id == country_id).first() is not None:
        raise api_error("country_in_use", status.HTTP_400_BAD_REQUEST)
    if db.query(TaxCode.id).filter(TaxCode.country_id == country_id).first() is not None:
        raise api_error("country_in_use", status.HTTP_400_BAD_REQUEST)


def assert_tax_code_deletable(db: Session, tax_code_id: int) -> None:
    if (
        db.query(Organisation.id)
        .filter(Organisation.default_tax_code_id == tax_code_id)
        .first()
        is not None
    ):
        raise api_error("tax_code_in_use", status.HTTP_400_BAD_REQUEST)
    if db.query(Article.id).filter(Article.tax_code_id == tax_code_id).first() is not None:
        raise api_error("tax_code_in_use", status.HTTP_400_BAD_REQUEST)
