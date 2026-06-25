
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import PaymentType, User
from ..payment_type_reference import assert_payment_type_deletable, get_payment_type_or_404
from ..payment_types_config import refresh_payment_types_cache
from ..tenancy import get_current_platform_admin

router = APIRouter()


def _raise_payment_type_slug_exists() -> None:
    raise api_error("payment_type_slug_exists", status.HTTP_400_BAD_REQUEST)


class PaymentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    sort_order: int
    is_active: bool


class PaymentTypeCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=32)
    sort_order: int = 0
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        slug = value.strip().lower()
        if not slug.replace("_", "").isalnum():
            raise ValueError("slug must be alphanumeric with optional underscores")
        return slug


class PaymentTypeUpdate(BaseModel):
    slug: str | None = Field(None, min_length=1, max_length=32)
    sort_order: int | None = None
    is_active: bool | None = None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        slug = value.strip().lower()
        if not slug.replace("_", "").isalnum():
            raise ValueError("slug must be alphanumeric with optional underscores")
        return slug


def _payment_type_response(payment_type: PaymentType) -> dict:
    return {
        "id": payment_type.id,
        "slug": payment_type.slug,
        "sort_order": payment_type.sort_order,
        "is_active": bool(payment_type.is_active),
    }


@router.get("/", response_model=list[PaymentTypeRead])
def list_payment_types(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(PaymentType).order_by(PaymentType.sort_order, PaymentType.slug)
    if active_only:
        query = query.filter(PaymentType.is_active.is_(True))
    return [_payment_type_response(row) for row in query.all()]


@router.get("/{payment_type_id}", response_model=PaymentTypeRead)
def read_payment_type(
    payment_type_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _payment_type_response(get_payment_type_or_404(db, payment_type_id))


@router.post("/", response_model=PaymentTypeRead, status_code=status.HTTP_201_CREATED)
def create_payment_type(
    body: PaymentTypeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    existing = db.query(PaymentType).filter(PaymentType.slug == body.slug).first()
    if existing:
        raise api_error("payment_type_slug_exists", status.HTTP_400_BAD_REQUEST)
    payment_type = PaymentType(
        slug=body.slug,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(payment_type)
    commit_or_raise(db, on_integrity=_raise_payment_type_slug_exists)
    db.refresh(payment_type)
    refresh_payment_types_cache(db)
    return _payment_type_response(payment_type)


@router.put("/{payment_type_id}", response_model=PaymentTypeRead)
def update_payment_type(
    payment_type_id: int,
    body: PaymentTypeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    payment_type = get_payment_type_or_404(db, payment_type_id)
    if body.slug is not None and body.slug != payment_type.slug:
        existing = db.query(PaymentType).filter(PaymentType.slug == body.slug).first()
        if existing:
            raise api_error("payment_type_slug_exists", status.HTTP_400_BAD_REQUEST)
        payment_type.slug = body.slug
    if body.sort_order is not None:
        payment_type.sort_order = body.sort_order
    if body.is_active is not None:
        payment_type.is_active = body.is_active
    commit_or_raise(db, on_integrity=_raise_payment_type_slug_exists)
    db.refresh(payment_type)
    refresh_payment_types_cache(db)
    return _payment_type_response(payment_type)


@router.delete("/{payment_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_type(
    payment_type_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_platform_admin),
):
    payment_type = get_payment_type_or_404(db, payment_type_id)
    assert_payment_type_deletable(db, payment_type)
    db.delete(payment_type)
    commit_or_raise(db)
    refresh_payment_types_cache(db)
    return None
