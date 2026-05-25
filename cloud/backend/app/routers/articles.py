from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..additions import replace_addition_links, serialize_links_for_admin, validate_base_article
from ..models import Article, ArticleCategory, Organisation, User
from ..auth_deps import get_current_user
from ..deps import get_db
from ..tenancy import TenantContext, ensure_user_can_use_organisation, get_current_tenant
from ..user_access import can_manage_tenant

router = APIRouter()


class ArticleBase(BaseModel):
    name: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1, max_length=22)
    price: float
    is_addition: bool = False
    monitor_stock: bool = False
    in_stock: int | None = Field(None, ge=0)
    article_category_id: int

    @model_validator(mode="after")
    def normalize_stock(self):
        if not self.monitor_stock:
            self.in_stock = None
        elif self.in_stock is None:
            self.in_stock = 0
        return self


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    label: str | None = Field(None, min_length=1, max_length=22)
    price: float | None = None
    is_addition: bool | None = None
    monitor_stock: bool | None = None
    in_stock: int | None = Field(None, ge=0)
    article_category_id: int | None = None


class ArticleRead(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_category_name: str
    organisation_id: int
    organisation_name: str


class ArticleAdditionLinkIn(BaseModel):
    addition_article_id: int
    sort_order: int | None = None


class ArticleAdditionsUpdateIn(BaseModel):
    items: List[ArticleAdditionLinkIn] = Field(default_factory=list)


class ArticleAdditionsRead(BaseModel):
    items: List[dict]


def article_response(article: Article) -> dict:
    category = article.article_category
    organisation = category.organisation if category else None
    return {
        "id": article.id,
        "name": article.name,
        "label": article.label,
        "price": article.price,
        "is_addition": bool(article.is_addition),
        "monitor_stock": article.monitor_stock,
        "in_stock": article.in_stock,
        "article_category_id": article.article_category_id,
        "article_category_name": category.name if category else "",
        "organisation_id": organisation.id if organisation else None,
        "organisation_name": organisation.name if organisation else "",
    }


def readable_articles_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(Article)
        .options(joinedload(Article.article_category).joinedload(ArticleCategory.organisation))
        .join(Article.article_category)
        .join(ArticleCategory.organisation)
        .filter(Organisation.hire_company_id == hire_company_id)
    )
    if can_manage_tenant(current_user):
        return query
    return query.join(Organisation.users).filter(User.id == current_user.id)


def readable_categories_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(ArticleCategory)
        .options(joinedload(ArticleCategory.organisation))
        .join(ArticleCategory.organisation)
        .filter(Organisation.hire_company_id == hire_company_id)
    )
    if can_manage_tenant(current_user):
        return query
    return query.join(Organisation.users).filter(User.id == current_user.id)


def ensure_user_can_use_category(
    db: Session, current_user: User, category_id: int, hire_company_id: int
) -> ArticleCategory:
    category = (
        readable_categories_query(db, current_user, hire_company_id)
        .filter(ArticleCategory.id == category_id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article category not found")
    return category


def _get_readable_article(
    db: Session, current_user: User, article_id: int, hire_company_id: int
) -> Article | None:
    return (
        readable_articles_query(db, current_user, hire_company_id)
        .filter(Article.id == article_id)
        .first()
    )


@router.get("/", response_model=List[ArticleRead])
def read_articles(
    is_addition: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    query = readable_articles_query(db, current_user, tenant.hire_company_id)
    if is_addition is not None:
        query = query.filter(Article.is_addition.is_(is_addition))
    articles = query.order_by(Article.name).all()
    return [article_response(article) for article in articles]


@router.get("/{article_id}/additions", response_model=ArticleAdditionsRead)
def read_article_additions(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    article = _get_readable_article(db, current_user, article_id, tenant.hire_company_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    validate_base_article(db, article_id)
    return ArticleAdditionsRead(items=serialize_links_for_admin(db, article))


@router.put("/{article_id}/additions", response_model=ArticleAdditionsRead)
def put_article_additions(
    article_id: int,
    body: ArticleAdditionsUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    article = _get_readable_article(db, current_user, article_id, tenant.hire_company_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    base = validate_base_article(db, article_id)
    try:
        replace_addition_links(
            db,
            base,
            [{"addition_article_id": i.addition_article_id, "sort_order": i.sort_order} for i in body.items],
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return ArticleAdditionsRead(items=serialize_links_for_admin(db, base))


@router.get("/{article_id}", response_model=ArticleRead)
def read_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    article = _get_readable_article(db, current_user, article_id, tenant.hire_company_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article_response(article)


@router.post("/", response_model=ArticleRead)
def create_article(
    article_in: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    category = ensure_user_can_use_category(db, current_user, article_in.article_category_id, tenant.hire_company_id)
    article = Article(
        name=article_in.name,
        label=article_in.label,
        price=article_in.price,
        is_addition=article_in.is_addition,
        monitor_stock=article_in.monitor_stock,
        in_stock=article_in.in_stock,
        article_category_id=category.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article_response(article)


@router.put("/{article_id}", response_model=ArticleRead)
def update_article(
    article_id: int,
    article_in: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    article = _get_readable_article(db, current_user, article_id, tenant.hire_company_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    if article_in.article_category_id is not None:
        category = ensure_user_can_use_category(db, current_user, article_in.article_category_id, tenant.hire_company_id)
        article.article_category_id = category.id
    if article_in.name is not None:
        article.name = article_in.name
    if article_in.label is not None:
        article.label = article_in.label
    if article_in.price is not None:
        article.price = article_in.price
    if article_in.is_addition is not None:
        article.is_addition = article_in.is_addition
    if article_in.monitor_stock is not None:
        article.monitor_stock = article_in.monitor_stock
    if article_in.in_stock is not None:
        article.in_stock = article_in.in_stock
    if not article.monitor_stock:
        article.in_stock = None
    elif article.in_stock is None:
        article.in_stock = 0

    db.commit()
    db.refresh(article)
    return article_response(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    article = _get_readable_article(db, current_user, article_id, tenant.hire_company_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    db.delete(article)
    db.commit()
    return None
