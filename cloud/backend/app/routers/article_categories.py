from typing import List

from fastapi import APIRouter, Depends, status
from ..i18n.errors import api_error
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..models import Article, ArticleCategory, Organisation, User
from ..auth_deps import get_current_user
from ..deps import get_db
from ..tenancy import TenantContext, ensure_user_can_use_organisation, get_current_tenant
from ..user_access import can_manage_tenant

router = APIRouter()


class ArticleCategoryBase(BaseModel):
    name: str = Field(..., min_length=1)
    organisation_id: int


class ArticleCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    organisation_id: int | None = None


class ArticleCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    organisation_id: int | None = None


class ArticleCategoryRead(ArticleCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_name: str
    article_count: int


def category_response(category: ArticleCategory) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "organisation_id": category.organisation_id,
        "organisation_name": category.organisation.name if category.organisation else "",
        "article_count": len(category.articles or []),
    }


def readable_categories_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(ArticleCategory)
        .options(
            joinedload(ArticleCategory.organisation),
            joinedload(ArticleCategory.articles),
        )
        .join(ArticleCategory.organisation)
        .filter(Organisation.hire_company_id == hire_company_id)
    )
    if can_manage_tenant(current_user):
        return query
    return query.join(Organisation.users).filter(User.id == current_user.id)


@router.get("/", response_model=List[ArticleCategoryRead])
def read_article_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    categories = (
        readable_categories_query(db, current_user, tenant.hire_company_id)
        .order_by(ArticleCategory.name)
        .all()
    )
    return [category_response(category) for category in categories]


@router.get("/{category_id}", response_model=ArticleCategoryRead)
def read_article_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    category = (
        readable_categories_query(db, current_user, tenant.hire_company_id)
        .filter(ArticleCategory.id == category_id)
        .first()
    )
    if not category:
        raise api_error("article_category_not_found", status.HTTP_404_NOT_FOUND)
    return category_response(category)


@router.post("/", response_model=ArticleCategoryRead)
def create_article_category(
    category_in: ArticleCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    organisation = ensure_user_can_use_organisation(
        db, current_user, category_in.organisation_id, tenant.hire_company_id
    )
    category = ArticleCategory(name=category_in.name, organisation_id=organisation.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category_response(category)


@router.put("/{category_id}", response_model=ArticleCategoryRead)
def update_article_category(
    category_id: int,
    category_in: ArticleCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    category = (
        readable_categories_query(db, current_user, tenant.hire_company_id)
        .filter(ArticleCategory.id == category_id)
        .first()
    )
    if not category:
        raise api_error("article_category_not_found", status.HTTP_404_NOT_FOUND)

    if category_in.organisation_id is not None:
        if db.query(Article).filter(Article.article_category_id == category.id).count():
            raise api_error("cannot_move_category_with_articles", status.HTTP_422_UNPROCESSABLE_ENTITY)
        organisation = ensure_user_can_use_organisation(
            db, current_user, category_in.organisation_id, tenant.hire_company_id
        )
        category.organisation_id = organisation.id
    if category_in.name is not None:
        category.name = category_in.name

    db.commit()
    db.refresh(category)
    return category_response(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    category = (
        readable_categories_query(db, current_user, tenant.hire_company_id)
        .filter(ArticleCategory.id == category_id)
        .first()
    )
    if not category:
        raise api_error("article_category_not_found", status.HTTP_404_NOT_FOUND)
    if db.query(Article).filter(Article.article_category_id == category.id).count():
        raise api_error("cannot_delete_category_with_articles", status.HTTP_422_UNPROCESSABLE_ENTITY)
    db.delete(category)
    db.commit()
    return None
