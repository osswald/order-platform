"""Rental Zubehör line CRUD (nested under rentals)."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import RentalZubehoerCatalogItem, RentalZubehoerLine
from ..rental_service import get_rental_in_tenant
from ..tenancy import TenantContext, get_current_tenant_admin

router = APIRouter()


class RentalZubehoerLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rental_id: int
    catalog_item_id: int | None
    label: str
    quantity: int | None
    sort_order: int


class RentalZubehoerLineCreate(BaseModel):
    catalog_item_id: int | None = None
    label: str | None = Field(None, min_length=1, max_length=255)
    quantity: int | None = Field(None, ge=1)
    sort_order: int = 0

    @model_validator(mode="after")
    def require_label_or_catalog(self):
        if self.catalog_item_id is None and not (self.label or "").strip():
            raise ValueError("label or catalog_item_id required")
        return self


class RentalZubehoerLineUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=255)
    quantity: int | None = Field(None, ge=1)
    sort_order: int | None = None


def _line_to_read(row: RentalZubehoerLine) -> RentalZubehoerLineRead:
    return RentalZubehoerLineRead(
        id=row.id,
        rental_id=row.rental_id,
        catalog_item_id=row.catalog_item_id,
        label=row.label,
        quantity=row.quantity,
        sort_order=row.sort_order,
    )


def _get_line_on_rental(
    db: Session,
    rental_id: int,
    line_id: int,
    hire_company_id: int,
) -> RentalZubehoerLine:
    rental = get_rental_in_tenant(db, rental_id, hire_company_id)
    row = next((line for line in (rental.zubehoer_lines or []) if line.id == line_id), None)
    if row is None:
        raise api_error("rental_zubehoer_line_not_found", status.HTTP_404_NOT_FOUND)
    return row


def _resolve_line_fields(
    db: Session,
    *,
    hire_company_id: int,
    body: RentalZubehoerLineCreate,
) -> tuple[str, int | None, int | None]:
    if body.catalog_item_id is not None:
        catalog = (
            db.query(RentalZubehoerCatalogItem)
            .filter(
                RentalZubehoerCatalogItem.id == body.catalog_item_id,
                RentalZubehoerCatalogItem.hire_company_id == hire_company_id,
            )
            .first()
        )
        if catalog is None:
            raise api_error("rental_zubehoer_catalog_not_found", status.HTTP_404_NOT_FOUND)
        label = catalog.name
        quantity = body.quantity if "quantity" in body.model_fields_set else catalog.default_quantity
        return label, quantity, catalog.id
    label = (body.label or "").strip()
    return label, body.quantity, None


@router.get("/{rental_id}/zubehoer-lines", response_model=list[RentalZubehoerLineRead])
def list_zubehoer_lines(
    rental_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    lines = sorted(rental.zubehoer_lines or [], key=lambda row: (row.sort_order, row.id))
    return [_line_to_read(row) for row in lines]


@router.post("/{rental_id}/zubehoer-lines", response_model=RentalZubehoerLineRead, status_code=status.HTTP_201_CREATED)
def create_zubehoer_line(
    rental_id: int,
    body: RentalZubehoerLineCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rental = get_rental_in_tenant(db, rental_id, tenant.hire_company_id)
    label, quantity, catalog_id = _resolve_line_fields(
        db,
        hire_company_id=tenant.hire_company_id,
        body=body,
    )
    row = RentalZubehoerLine(
        rental_id=rental.id,
        catalog_item_id=catalog_id,
        label=label,
        quantity=quantity,
        sort_order=body.sort_order,
    )
    db.add(row)
    commit_or_raise(db)
    db.refresh(row)
    return _line_to_read(row)


@router.patch("/{rental_id}/zubehoer-lines/{line_id}", response_model=RentalZubehoerLineRead)
def update_zubehoer_line(
    rental_id: int,
    line_id: int,
    body: RentalZubehoerLineUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    row = _get_line_on_rental(db, rental_id, line_id, tenant.hire_company_id)
    if body.label is not None:
        row.label = body.label.strip()
    if "quantity" in body.model_fields_set:
        row.quantity = body.quantity
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    commit_or_raise(db)
    db.refresh(row)
    return _line_to_read(row)


@router.delete("/{rental_id}/zubehoer-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zubehoer_line(
    rental_id: int,
    line_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    row = _get_line_on_rental(db, rental_id, line_id, tenant.hire_company_id)
    db.delete(row)
    commit_or_raise(db)
    return None
