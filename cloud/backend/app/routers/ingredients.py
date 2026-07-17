"""Ingredient catalog CRUD."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import ArticleIngredientLink, Ingredient, Organisation, User
from ..tenancy import TenantContext, ensure_user_can_use_organisation, get_current_tenant
from ..user_access import can_manage_tenant

router = APIRouter()


class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1)
    unit: str | None = Field(None, max_length=32)
    is_active: bool = True


class IngredientCreate(IngredientBase):
    organisation_id: int | None = None


class IngredientUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    unit: str | None = Field(None, max_length=32)
    is_active: bool | None = None


class IngredientRead(IngredientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_id: int
    organisation_name: str
    usage_count: int = 0


def ingredient_response(ingredient: Ingredient, usage_count: int = 0) -> dict:
    return {
        "id": ingredient.id,
        "name": ingredient.name,
        "unit": ingredient.unit,
        "is_active": bool(ingredient.is_active),
        "organisation_id": ingredient.organisation_id,
        "organisation_name": ingredient.organisation.name if ingredient.organisation else "",
        "usage_count": usage_count,
    }


def readable_ingredients_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(Ingredient)
        .options(joinedload(Ingredient.organisation))
        .join(Ingredient.organisation)
        .filter(Organisation.hire_company_id == hire_company_id)
    )
    if can_manage_tenant(current_user):
        return query
    return query.join(Organisation.users).filter(User.id == current_user.id)


def _usage_counts(db: Session, ingredient_ids: list[int]) -> dict[int, int]:
    if not ingredient_ids:
        return {}
    rows = (
        db.query(ArticleIngredientLink.ingredient_id)
        .filter(ArticleIngredientLink.ingredient_id.in_(ingredient_ids))
        .all()
    )
    counts: dict[int, int] = {}
    for (iid,) in rows:
        counts[iid] = counts.get(iid, 0) + 1
    return counts


@router.get("/", response_model=list[IngredientRead])
def read_ingredients(
    organisation_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    query = readable_ingredients_query(db, current_user, tenant.hire_company_id)
    if organisation_id is not None:
        query = query.filter(Ingredient.organisation_id == organisation_id)
    ingredients = query.order_by(Ingredient.name).all()
    counts = _usage_counts(db, [i.id for i in ingredients])
    return [ingredient_response(i, counts.get(i.id, 0)) for i in ingredients]


@router.get("/{ingredient_id}", response_model=IngredientRead)
def read_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ingredient = (
        readable_ingredients_query(db, current_user, tenant.hire_company_id)
        .filter(Ingredient.id == ingredient_id)
        .first()
    )
    if not ingredient:
        raise api_error("ingredient_not_found", status.HTTP_404_NOT_FOUND)
    counts = _usage_counts(db, [ingredient.id])
    return ingredient_response(ingredient, counts.get(ingredient.id, 0))


@router.post("/", response_model=IngredientRead)
def create_ingredient(
    ingredient_in: IngredientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    if ingredient_in.organisation_id is None:
        raise api_error("organisation_required", status.HTTP_400_BAD_REQUEST)
    organisation = ensure_user_can_use_organisation(
        db, current_user, ingredient_in.organisation_id, tenant.hire_company_id
    )
    from ..ingredients import ensure_ingredients_enabled

    ensure_ingredients_enabled(db, organisation.id)
    ingredient = Ingredient(
        name=ingredient_in.name,
        unit=ingredient_in.unit,
        is_active=ingredient_in.is_active,
        organisation_id=organisation.id,
    )
    db.add(ingredient)
    commit_or_raise(db)
    db.refresh(ingredient)
    return ingredient_response(ingredient, 0)


@router.put("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: int,
    ingredient_in: IngredientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ingredient = (
        readable_ingredients_query(db, current_user, tenant.hire_company_id)
        .filter(Ingredient.id == ingredient_id)
        .first()
    )
    if not ingredient:
        raise api_error("ingredient_not_found", status.HTTP_404_NOT_FOUND)
    if ingredient_in.name is not None:
        ingredient.name = ingredient_in.name
    if ingredient_in.unit is not None:
        ingredient.unit = ingredient_in.unit or None
    if ingredient_in.is_active is not None:
        ingredient.is_active = bool(ingredient_in.is_active)
    commit_or_raise(db)
    db.refresh(ingredient)
    counts = _usage_counts(db, [ingredient.id])
    return ingredient_response(ingredient, counts.get(ingredient.id, 0))


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ingredient = (
        readable_ingredients_query(db, current_user, tenant.hire_company_id)
        .filter(Ingredient.id == ingredient_id)
        .first()
    )
    if not ingredient:
        raise api_error("ingredient_not_found", status.HTTP_404_NOT_FOUND)
    in_use = (
        db.query(ArticleIngredientLink)
        .filter(ArticleIngredientLink.ingredient_id == ingredient_id)
        .first()
    )
    if in_use:
        raise api_error("ingredient_in_use", status.HTTP_400_BAD_REQUEST)
    db.delete(ingredient)
    commit_or_raise(db)
    return None
