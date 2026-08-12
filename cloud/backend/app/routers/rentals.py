from calendar import monthrange
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.deps import get_locale
from ..i18n.errors import api_error
from ..models import Appliance, ApplianceLending, HireCompany, Rental
from ..pdf.documents.rental_packing import build_rental_packing_pdf
from ..pdf.formatting import safe_filename
from ..pdf.response import pdf_download_response
from ..pdf.settings import PdfReportSettings
from ..rental_service import (
    FLEET_TYPE_ORDER,
    apply_rental_dates,
    assign_appliance_to_rental,
    delete_rental_if_allowed,
    get_appliance_in_tenant,
    get_org_in_tenant,
    get_rental_in_tenant,
    lending_segment,
    rental_display_name,
    rental_is_filled,
    utc_today,
)
from ..tenancy import TenantContext, get_current_tenant_admin
from . import rental_zubehoer_lines
from .rental_zubehoer_lines import RentalZubehoerLineRead, _line_to_read

router = APIRouter()
router.include_router(rental_zubehoer_lines.router)


class RentalLendingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appliance_id: int
    appliance_name: str | None
    appliance_type: str
    start_date: date
    end_date: date
    returned_at: datetime | None
    segment: str


class RentalRead(BaseModel):
    id: int
    hire_company_id: int
    organisation_id: int
    organisation_name: str
    start_date: date
    end_date: date
    label: str | None
    display_name: str
    filled: bool
    lendings: list[RentalLendingRead]
    zubehoer_lines: list[RentalZubehoerLineRead] = Field(default_factory=list)


class RentalCreate(BaseModel):
    organisation_id: int
    start_date: date
    end_date: date
    label: str | None = Field(None, max_length=255)
    appliance_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class RentalUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    label: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class RentalAssignAppliance(BaseModel):
    appliance_id: int


class FleetOccupancyRead(BaseModel):
    rental_id: int
    display_name: str
    organisation_id: int
    start_date: date
    end_date: date


class FleetApplianceRead(BaseModel):
    id: int
    name: str | None
    type: str
    occupancies: list[FleetOccupancyRead]


class FleetTypeGroupRead(BaseModel):
    type: str
    appliances: list[FleetApplianceRead]


class FleetRead(BaseModel):
    year: int
    month: int
    groups: list[FleetTypeGroupRead]


def _lending_to_read(row: ApplianceLending, today: date) -> RentalLendingRead:
    appliance = row.appliance
    return RentalLendingRead(
        id=row.id,
        appliance_id=row.appliance_id,
        appliance_name=appliance.name if appliance is not None else None,
        appliance_type=appliance.type if appliance is not None else "",
        start_date=row.start_date,
        end_date=row.end_date,
        returned_at=row.returned_at,
        segment=lending_segment(row, today),
    )


def _rental_to_read(rental: Rental, today: date) -> RentalRead:
    org_name = rental.organisation.name if rental.organisation is not None else ""
    lendings = sorted(rental.lendings or [], key=lambda row: (row.start_date, row.id), reverse=True)
    zubehoer_lines = sorted(rental.zubehoer_lines or [], key=lambda row: (row.sort_order, row.id))
    return RentalRead(
        id=rental.id,
        hire_company_id=rental.hire_company_id,
        organisation_id=rental.organisation_id,
        organisation_name=org_name,
        start_date=rental.start_date,
        end_date=rental.end_date,
        label=rental.label,
        display_name=rental_display_name(rental),
        filled=rental_is_filled(rental),
        lendings=[_lending_to_read(row, today) for row in lendings],
        zubehoer_lines=[_line_to_read(row) for row in zubehoer_lines],
    )


@router.get("/", response_model=list[RentalRead])
def list_rentals(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    organisation_id: int | None = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    if (date_from is None) != (date_to is None):
        raise api_error("rental_range_incomplete", status.HTTP_422_UNPROCESSABLE_CONTENT)
    if date_from is not None and date_to is not None and date_to < date_from:
        raise api_error("rental_end_before_start", status.HTTP_422_UNPROCESSABLE_CONTENT)

    query = (
        db.query(Rental)
        .options(
            joinedload(Rental.organisation),
            joinedload(Rental.lendings).joinedload(ApplianceLending.appliance),
            joinedload(Rental.zubehoer_lines),
        )
        .filter(Rental.hire_company_id == tenant.hire_company_id)
    )
    if organisation_id is not None:
        get_org_in_tenant(db, organisation_id, tenant.hire_company_id)
        query = query.filter(Rental.organisation_id == organisation_id)
    if date_from is not None and date_to is not None:
        query = query.filter(Rental.start_date <= date_to, Rental.end_date >= date_from)
    rows = query.order_by(Rental.start_date, Rental.id).all()
    today = utc_today()
    return [_rental_to_read(row, today) for row in rows]


@router.get("/fleet", response_model=FleetRead)
def read_fleet(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    appliances = (
        db.query(Appliance)
        .filter(
            Appliance.hire_company_id == tenant.hire_company_id,
            Appliance.is_hosted_virtual.is_(False),
        )
        .order_by(Appliance.type, Appliance.id)
        .all()
    )
    appliance_ids = [row.id for row in appliances]
    occupancies_by_appliance: dict[int, list[FleetOccupancyRead]] = {aid: [] for aid in appliance_ids}
    if appliance_ids:
        lendings = (
            db.query(ApplianceLending)
            .options(
                joinedload(ApplianceLending.rental).joinedload(Rental.organisation),
                joinedload(ApplianceLending.appliance),
            )
            .filter(
                ApplianceLending.appliance_id.in_(appliance_ids),
                ApplianceLending.returned_at.is_(None),
                ApplianceLending.start_date <= month_end,
                ApplianceLending.end_date >= month_start,
            )
            .all()
        )
        for row in lendings:
            rental = row.rental
            if rental is None:
                continue
            occupancies_by_appliance[row.appliance_id].append(
                FleetOccupancyRead(
                    rental_id=rental.id,
                    display_name=rental_display_name(rental),
                    organisation_id=rental.organisation_id,
                    start_date=row.start_date,
                    end_date=row.end_date,
                )
            )

    grouped: dict[str, list[FleetApplianceRead]] = {}
    for appliance in appliances:
        grouped.setdefault(appliance.type, []).append(
            FleetApplianceRead(
                id=appliance.id,
                name=appliance.name,
                type=appliance.type,
                occupancies=occupancies_by_appliance.get(appliance.id, []),
            )
        )
    extra_types = [typ for typ in grouped if typ not in FLEET_TYPE_ORDER]
    type_order = list(FLEET_TYPE_ORDER) + sorted(extra_types)
    groups = [
        FleetTypeGroupRead(type=typ, appliances=grouped[typ])
        for typ in type_order
        if typ in grouped
    ]
    return FleetRead(year=year, month=month, groups=groups)


@router.get("/{rental_id}", response_model=RentalRead)
def read_rental(
    rental_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    return _rental_to_read(rental, utc_today())


@router.post("/", response_model=RentalRead, status_code=status.HTTP_201_CREATED)
def create_rental(
    body: RentalCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    org = get_org_in_tenant(db, body.organisation_id, tenant.hire_company_id)
    label = (body.label or "").strip() or None
    rental = Rental(
        hire_company_id=tenant.hire_company_id,
        organisation_id=org.id,
        start_date=body.start_date,
        end_date=body.end_date,
        label=label,
    )
    db.add(rental)
    db.flush()
    seen: set[int] = set()
    for appliance_id in body.appliance_ids:
        if appliance_id in seen:
            continue
        seen.add(appliance_id)
        appliance = get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
        assign_appliance_to_rental(db, rental, appliance)
    commit_or_raise(db)
    rental = get_rental_in_tenant(db, rental.id, tenant.hire_company_id)
    return _rental_to_read(rental, utc_today())


@router.patch("/{rental_id}", response_model=RentalRead)
def update_rental(
    rental_id: int,
    body: RentalUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    if body.label is not None:
        rental.label = body.label.strip() or None
    new_start = body.start_date if body.start_date is not None else rental.start_date
    new_end = body.end_date if body.end_date is not None else rental.end_date
    if new_start != rental.start_date or new_end != rental.end_date:
        apply_rental_dates(db, rental, new_start, new_end)
    commit_or_raise(db)
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    return _rental_to_read(rental, utc_today())


@router.delete("/{rental_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rental(
    rental_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    delete_rental_if_allowed(db, rental, utc_today())
    commit_or_raise(db)
    return None


@router.post("/{rental_id}/appliances", response_model=RentalRead)
def assign_rental_appliance(
    rental_id: int,
    body: RentalAssignAppliance,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    appliance = get_appliance_in_tenant(db, body.appliance_id, tenant.hire_company_id)
    assign_appliance_to_rental(db, rental, appliance)
    commit_or_raise(db)
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    return _rental_to_read(rental, utc_today())


@router.delete("/{rental_id}/lendings/{lending_id}", response_model=RentalRead)
def unassign_rental_lending(
    rental_id: int,
    lending_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    lending = next((row for row in (rental.lendings or []) if row.id == lending_id), None)
    if lending is None:
        raise api_error("lending_not_found", status.HTTP_404_NOT_FOUND)
    today = utc_today()
    if lending.returned_at is not None:
        raise api_error("lending_already_returned", status.HTTP_400_BAD_REQUEST)
    if lending.start_date > today:
        db.delete(lending)
    else:
        lending.returned_at = datetime.now(UTC)
    commit_or_raise(db)
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    return _rental_to_read(rental, today)


@router.get("/{rental_id}/packing-list.pdf")
def read_rental_packing_pdf(
    rental_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
    locale: str = Depends(get_locale),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    hire_company = db.query(HireCompany).filter(HireCompany.id == tenant.hire_company_id).first()
    pdf_bytes = build_rental_packing_pdf(
        rental=rental,
        hire_company=hire_company,
        settings=PdfReportSettings(locale=locale),
    )
    filename = f"Packliste-{safe_filename(rental_display_name(rental))}.pdf"
    return pdf_download_response(pdf_bytes, filename)
