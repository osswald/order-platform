"""Rental container helpers: display name, overlap, assign, date moves."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import status
from sqlalchemy.orm import Session, joinedload

from .i18n.errors import api_error
from .models import Appliance, ApplianceLending, Organisation, Rental

FLEET_TYPE_ORDER = ("server", "printer", "mobile", "tablet", "router", "ap")


def utc_today() -> date:
    return datetime.now(UTC).date()


def rental_display_name(rental: Rental) -> str:
    label = (rental.label or "").strip()
    if label:
        return label
    org = rental.organisation
    return org.name if org is not None else ""


def rental_is_filled(rental: Rental) -> bool:
    return any(row.returned_at is None for row in (rental.lendings or []))


def lending_segment(lending: ApplianceLending, today: date) -> str:
    if lending.returned_at is not None:
        return "past"
    if lending.start_date > today:
        return "future"
    if lending.end_date < today:
        return "past"
    if lending.start_date <= today <= lending.end_date:
        return "current"
    return "past"


def get_rental_in_tenant(db: Session, rental_id: int, hire_company_id: int) -> Rental:
    rental = (
        db.query(Rental)
        .options(
            joinedload(Rental.organisation),
            joinedload(Rental.lendings).joinedload(ApplianceLending.appliance),
            joinedload(Rental.zubehoer_lines),
        )
        .filter(Rental.id == rental_id, Rental.hire_company_id == hire_company_id)
        .first()
    )
    if rental is None:
        raise api_error("rental_not_found", status.HTTP_404_NOT_FOUND)
    return rental


def assert_valid_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise api_error("rental_end_before_start", status.HTTP_422_UNPROCESSABLE_CONTENT)


def ranges_strictly_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """True when inclusive ranges share more than a single endpoint day (handover touch allowed)."""
    return start_a < end_b and start_b < end_a


def find_open_overlap(
    db: Session,
    *,
    appliance_id: int,
    start_date: date,
    end_date: date,
    exclude_lending_id: int | None = None,
) -> ApplianceLending | None:
    # Endpoint-touch (A ends D, B starts D) is allowed; interior overlap is not.
    query = db.query(ApplianceLending).filter(
        ApplianceLending.appliance_id == appliance_id,
        ApplianceLending.returned_at.is_(None),
        ApplianceLending.start_date < end_date,
        ApplianceLending.end_date > start_date,
    )
    if exclude_lending_id is not None:
        query = query.filter(ApplianceLending.id != exclude_lending_id)
    return query.first()


def open_lendings_covering_day(
    lendings: list[ApplianceLending] | tuple[ApplianceLending, ...] | None,
    day: date,
) -> list[ApplianceLending]:
    return [
        row
        for row in (lendings or [])
        if row.returned_at is None and row.start_date <= day <= row.end_date
    ]


def select_active_lending_for_day(
    lendings: list[ApplianceLending] | tuple[ApplianceLending, ...] | None,
    day: date,
) -> ApplianceLending | None:
    """Prefer the open lending that starts on ``day`` (handover arrival); else lowest id."""
    covering = open_lendings_covering_day(lendings, day)
    if not covering:
        return None
    starting = [row for row in covering if row.start_date == day]
    pool = starting if starting else covering
    return min(pool, key=lambda row: row.id)


def index_active_lendings_by_appliance(
    lendings: list[ApplianceLending] | tuple[ApplianceLending, ...] | None,
    day: date,
) -> dict[int, ApplianceLending]:
    by_appliance: dict[int, list[ApplianceLending]] = {}
    for row in lendings or []:
        if row.returned_at is not None:
            continue
        if not (row.start_date <= day <= row.end_date):
            continue
        by_appliance.setdefault(row.appliance_id, []).append(row)
    result: dict[int, ApplianceLending] = {}
    for appliance_id, group in by_appliance.items():
        chosen = select_active_lending_for_day(group, day)
        if chosen is not None:
            result[appliance_id] = chosen
    return result


def assign_appliance_to_rental(
    db: Session,
    rental: Rental,
    appliance: Appliance,
) -> ApplianceLending:
    if appliance.is_hosted_virtual:
        raise api_error("appliance_not_lendable", status.HTTP_400_BAD_REQUEST)
    if appliance.hire_company_id != rental.hire_company_id:
        raise api_error("appliance_not_in_verleiher", status.HTTP_403_FORBIDDEN)
    if find_open_overlap(
        db,
        appliance_id=appliance.id,
        start_date=rental.start_date,
        end_date=rental.end_date,
    ):
        raise api_error("lending_overlap", status.HTTP_400_BAD_REQUEST)
    lending = ApplianceLending(
        rental_id=rental.id,
        appliance_id=appliance.id,
        organisation_id=rental.organisation_id,
        start_date=rental.start_date,
        end_date=rental.end_date,
        returned_at=None,
    )
    db.add(lending)
    return lending


def apply_rental_dates(db: Session, rental: Rental, start_date: date, end_date: date) -> None:
    assert_valid_range(start_date, end_date)
    open_lendings = [row for row in (rental.lendings or []) if row.returned_at is None]
    for row in open_lendings:
        if find_open_overlap(
            db,
            appliance_id=row.appliance_id,
            start_date=start_date,
            end_date=end_date,
            exclude_lending_id=row.id,
        ):
            raise api_error("lending_overlap", status.HTTP_400_BAD_REQUEST)
    rental.start_date = start_date
    rental.end_date = end_date
    for row in open_lendings:
        row.start_date = start_date
        row.end_date = end_date


def rental_has_current_open_lending(rental: Rental, today: date) -> bool:
    return any(
        row.returned_at is None and row.start_date <= today
        for row in (rental.lendings or [])
    )


def rental_has_returned_lending(rental: Rental) -> bool:
    return any(row.returned_at is not None for row in (rental.lendings or []))


def delete_rental_if_allowed(db: Session, rental: Rental, today: date) -> None:
    if rental_has_current_open_lending(rental, today):
        raise api_error("rental_has_current_lending", status.HTTP_400_BAD_REQUEST)
    if rental_has_returned_lending(rental):
        raise api_error("rental_has_history", status.HTTP_400_BAD_REQUEST)
    db.delete(rental)


def get_appliance_in_tenant(db: Session, appliance_id: int, hire_company_id: int) -> Appliance:
    appliance = (
        db.query(Appliance)
        .filter(Appliance.id == appliance_id, Appliance.hire_company_id == hire_company_id)
        .first()
    )
    if appliance is None:
        raise api_error("appliance_not_found", status.HTTP_404_NOT_FOUND)
    return appliance


def get_org_in_tenant(db: Session, organisation_id: int, hire_company_id: int) -> Organisation:
    org = (
        db.query(Organisation)
        .filter(Organisation.id == organisation_id, Organisation.hire_company_id == hire_company_id)
        .first()
    )
    if org is None:
        raise api_error("organisation_not_in_verleiher", status.HTTP_403_FORBIDDEN)
    return org
