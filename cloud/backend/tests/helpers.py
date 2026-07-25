"""Shared helpers for cloud backend tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.models import Country
from sqlalchemy.orm import Session

STRIPE_FIXTURES = Path(__file__).parent / "fixtures" / "stripe"


def stripe_account_payload(name: str) -> dict[str, Any]:
    """Load a captured Stripe Accounts v2 retrieve payload."""
    return json.loads((STRIPE_FIXTURES / f"{name}.json").read_text())


def stripe_object(value: Any) -> Any:
    """Mimic the Stripe SDK, which returns nested objects rather than plain dicts."""
    if isinstance(value, dict):
        return SimpleNamespace(**{key: stripe_object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [stripe_object(item) for item in value]
    return value


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
