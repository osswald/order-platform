from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from ..i18n.errors import api_error
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from ..additions import replace_addition_links, serialize_links_for_admin, validate_base_article
from ..currency import organisation_currency
from ..accounting_validation import resolve_article_accounting_account_id, validate_article_accounting_account
from ..models import Article, ArticleCategory, Organisation, User
from ..tax_code_validation import validate_article_tax_code
from ..auth_deps import get_current_user
from ..deps import get_db
from ..tenancy import TenantContext, ensure_user_can_use_organisation, get_current_tenant
from ..user_access import can_manage_tenant

router = APIRouter()


class ArticleBase(BaseModel):
    name: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1, max_length=22)
    price: float
    import_article_number: str | None = None
    description: str | None = None
    unit: str | None = None
    accounting_account_id: int | None = None
    tax_code_id: int | None = None
    is_addition: bool = False
    article_category_id: int


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    label: str | None = Field(None, min_length=1, max_length=22)
    price: float | None = None
    import_article_number: str | None = None
    description: str | None = None
    unit: str | None = None
    accounting_account_id: int | None = None
    tax_code_id: int | None = None
    is_addition: bool | None = None
    article_category_id: int | None = None


class ArticleRead(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_category_name: str
    organisation_id: int
    organisation_name: str
    organisation_currency: str
    tax_code_name: str | None = None
    accounting_account_name: str | None = None
    accounting_account_number: str | None = None


class ArticleMinimalRead(BaseModel):
    id: int
    name: str
    label: str
    organisation_id: int | None
    is_addition: bool


class ArticleAdditionLinkIn(BaseModel):
    addition_article_id: int
    sort_order: int | None = None


class ArticleAdditionsUpdateIn(BaseModel):
    items: List[ArticleAdditionLinkIn] = Field(default_factory=list)


class ArticleAdditionsRead(BaseModel):
    items: List[dict]


def article_minimal_response(article: Article) -> ArticleMinimalRead:
    category = article.article_category
    organisation = category.organisation if category else None
    return ArticleMinimalRead(
        id=article.id,
        name=article.name,
        label=article.label,
        organisation_id=organisation.id if organisation else None,
        is_addition=bool(article.is_addition),
    )


def article_response(article: Article) -> ArticleRead:
    category = article.article_category
    organisation = category.organisation if category else None
    tax_code_name = article.tax_code.name if article.tax_code is not None else None
    accounting_account = article.accounting_account
    return ArticleRead(
        id=article.id,
        name=article.name,
        label=article.label,
        price=article.price,
        import_article_number=article.import_article_number,
        description=article.description,
        unit=article.unit,
        accounting_account_id=article.accounting_account_id,
        tax_code_id=article.tax_code_id,
        is_addition=bool(article.is_addition),
        article_category_id=article.article_category_id,
        article_category_name=category.name if category else "",
        organisation_id=organisation.id if organisation else 0,
        organisation_name=organisation.name if organisation else "",
        organisation_currency=organisation_currency(organisation),
        tax_code_name=tax_code_name,
        accounting_account_name=accounting_account.name if accounting_account else None,
        accounting_account_number=accounting_account.number if accounting_account else None,
    )


def readable_articles_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(Article)
        .options(
            joinedload(Article.article_category).joinedload(ArticleCategory.organisation),
            joinedload(Article.tax_code),
            joinedload(Article.accounting_account),
        )
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
        raise api_error("article_category_not_found", status.HTTP_404_NOT_FOUND)
    return category


def _get_readable_article(
    db: Session, current_user: User, article_id: int, hire_company_id: int
) -> Article | None:
    return (
        readable_articles_query(db, current_user, hire_company_id)
        .filter(Article.id == article_id)
        .first()
    )


@router.get("/", response_model=List[ArticleRead] | List[ArticleMinimalRead])
def read_articles(
    is_addition: bool | None = Query(None),
    organisation_id: int | None = Query(None),
    minimal: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    query = readable_articles_query(db, current_user, tenant.hire_company_id)
    if is_addition is not None:
        query = query.filter(Article.is_addition.is_(is_addition))
    if organisation_id is not None:
        query = query.filter(Organisation.id == organisation_id)
    articles = query.order_by(Article.name).all()
    if minimal:
        return [article_minimal_response(article) for article in articles]
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
        raise api_error("article_not_found", status.HTTP_404_NOT_FOUND)
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
        raise api_error("article_not_found", status.HTTP_404_NOT_FOUND)
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
        raise api_error("article_not_found", status.HTTP_404_NOT_FOUND)
    return article_response(article)


@router.post("/", response_model=ArticleRead)
def create_article(
    article_in: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    category = ensure_user_can_use_category(db, current_user, article_in.article_category_id, tenant.hire_company_id)
    organisation = category.organisation
    validate_article_tax_code(db, organisation, article_in.tax_code_id)
    accounting_account_id = resolve_article_accounting_account_id(
        db, organisation, category, article_in.accounting_account_id
    )
    article = Article(
        name=article_in.name,
        label=article_in.label,
        price=article_in.price,
        import_article_number=article_in.import_article_number,
        description=article_in.description,
        unit=article_in.unit,
        accounting_account_id=accounting_account_id,
        tax_code_id=article_in.tax_code_id if organisation.vat_liable else None,
        is_addition=article_in.is_addition,
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
        raise api_error("article_not_found", status.HTTP_404_NOT_FOUND)

    category = article.article_category
    if article_in.article_category_id is not None:
        category = ensure_user_can_use_category(db, current_user, article_in.article_category_id, tenant.hire_company_id)
        article.article_category_id = category.id
    organisation = category.organisation
    if article_in.name is not None:
        article.name = article_in.name
    if article_in.label is not None:
        article.label = article_in.label
    if article_in.price is not None:
        article.price = article_in.price
    update_fields = article_in.model_dump(exclude_unset=True)
    for field in ("import_article_number", "description", "unit"):
        if field in update_fields:
            setattr(article, field, update_fields[field])
    if "accounting_account_id" in update_fields:
        article.accounting_account_id = validate_article_accounting_account(
            db, organisation, update_fields["accounting_account_id"]
        )
    if "tax_code_id" in update_fields:
        validate_article_tax_code(db, organisation, update_fields["tax_code_id"])
        article.tax_code_id = update_fields["tax_code_id"] if organisation.vat_liable else None
    elif not organisation.vat_liable:
        article.tax_code_id = None
    if article_in.is_addition is not None:
        article.is_addition = article_in.is_addition

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
        raise api_error("article_not_found", status.HTTP_404_NOT_FOUND)
    db.delete(article)
    db.commit()
    return None
