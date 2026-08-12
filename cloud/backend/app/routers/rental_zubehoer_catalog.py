"""Tenant-scoped Zubehör catalog for rentals."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import RentalZubehoerCatalogItem
from ..tenancy import TenantContext, get_current_tenant_admin

router = APIRouter()


class RentalZubehoerCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    default_quantity: int | None
    sort_order: int
    is_active: bool


class RentalZubehoerCatalogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    default_quantity: int | None = Field(None, ge=1)
    sort_order: int = 0
    is_active: bool = True


class RentalZubehoerCatalogUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    default_quantity: int | None = Field(None, ge=1)
    sort_order: int | None = None
    is_active: bool | None = None


def _get_catalog_item_in_tenant(
    db: Session,
    item_id: int,
    hire_company_id: int,
) -> RentalZubehoerCatalogItem:
    row = (
        db.query(RentalZubehoerCatalogItem)
        .filter(
            RentalZubehoerCatalogItem.id == item_id,
            RentalZubehoerCatalogItem.hire_company_id == hire_company_id,
        )
        .first()
    )
    if row is None:
        raise api_error("rental_zubehoer_catalog_not_found", status.HTTP_404_NOT_FOUND)
    return row


@router.get("/", response_model=list[RentalZubehoerCatalogRead])
def list_catalog(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    rows = (
        db.query(RentalZubehoerCatalogItem)
        .filter(RentalZubehoerCatalogItem.hire_company_id == tenant.hire_company_id)
        .order_by(RentalZubehoerCatalogItem.sort_order, RentalZubehoerCatalogItem.id)
        .all()
    )
    return rows


@router.post("/", response_model=RentalZubehoerCatalogRead, status_code=status.HTTP_201_CREATED)
def create_catalog_item(
    body: RentalZubehoerCatalogCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    row = RentalZubehoerCatalogItem(
        hire_company_id=tenant.hire_company_id,
        name=body.name.strip(),
        default_quantity=body.default_quantity,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(row)
    commit_or_raise(db)
    db.refresh(row)
    return row


@router.patch("/{item_id}", response_model=RentalZubehoerCatalogRead)
def update_catalog_item(
    item_id: int,
    body: RentalZubehoerCatalogUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    row = _get_catalog_item_in_tenant(db, item_id, tenant.hire_company_id)
    if body.name is not None:
        row.name = body.name.strip()
    if "default_quantity" in body.model_fields_set:
        row.default_quantity = body.default_quantity
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
    commit_or_raise(db)
    db.refresh(row)
    return row


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    row = _get_catalog_item_in_tenant(db, item_id, tenant.hire_company_id)
    db.delete(row)
    commit_or_raise(db)
    return None
