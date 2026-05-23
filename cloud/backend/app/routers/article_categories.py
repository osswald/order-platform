from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ..models import Article, ArticleCategory, Organisation, User
from .auth import get_current_user, get_db

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
    id: int
    organisation_name: str
    article_count: int

    class Config:
        from_attributes = True


def category_response(category: ArticleCategory) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "organisation_id": category.organisation_id,
        "organisation_name": category.organisation.name if category.organisation else "",
        "article_count": len(category.articles or []),
    }


def readable_categories_query(db: Session, current_user: User):
    query = db.query(ArticleCategory).options(
        joinedload(ArticleCategory.organisation),
        joinedload(ArticleCategory.articles),
    )
    if current_user.is_superuser:
        return query
    return (
        query.join(ArticleCategory.organisation)
        .join(Organisation.users)
        .filter(User.id == current_user.id)
    )


def readable_organisations(db: Session, current_user: User) -> list[Organisation]:
    if current_user.is_superuser:
        return db.query(Organisation).order_by(Organisation.name).all()
    return sorted(current_user.organisations or [], key=lambda org: org.name.lower())


def ensure_organisation_exists(db: Session, organisation_id: int) -> Organisation:
    organisation = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not organisation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation


def ensure_user_can_use_organisation(
    db: Session,
    current_user: User,
    organisation_id: int | None,
) -> Organisation:
    organisations = readable_organisations(db, current_user)
    if organisation_id is None:
        if len(organisations) == 1:
            return organisations[0]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organisation is required when the user is linked to multiple organisations",
        )
    organisation = ensure_organisation_exists(db, organisation_id)
    if current_user.is_superuser:
        return organisation
    if not any(org.id == organisation.id for org in organisations):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this organisation")
    return organisation


@router.get("/", response_model=List[ArticleCategoryRead])
def read_article_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    categories = readable_categories_query(db, current_user).order_by(ArticleCategory.name).all()
    return [category_response(category) for category in categories]


@router.get("/{category_id}", response_model=ArticleCategoryRead)
def read_article_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = readable_categories_query(db, current_user).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article category not found")
    return category_response(category)


@router.post("/", response_model=ArticleCategoryRead)
def create_article_category(
    category_in: ArticleCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organisation = ensure_user_can_use_organisation(db, current_user, category_in.organisation_id)
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
):
    category = readable_categories_query(db, current_user).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article category not found")

    if category_in.organisation_id is not None:
        if db.query(Article).filter(Article.article_category_id == category.id).count():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot move category while articles are linked",
            )
        organisation = ensure_user_can_use_organisation(db, current_user, category_in.organisation_id)
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
):
    category = readable_categories_query(db, current_user).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article category not found")
    if db.query(Article).filter(Article.article_category_id == category.id).count():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot delete category while articles are linked",
        )
    db.delete(category)
    db.commit()
    return None
