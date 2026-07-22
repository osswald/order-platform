import re

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import Organisation, User
from ..rate_limit import USERS_RATE_LIMIT, limiter
from ..roles import (
    ALL_ROLES,
    ASSIGNABLE_BY_ORGANISATION_ADMIN,
    ROLE_MEMBER,
    ROLE_ORGANISATION_ADMIN,
    ROLE_PLATFORM_ADMIN,
    ROLE_TENANT_ADMIN,
)
from ..security import get_password_hash
from ..tenancy import (
    TenantContext,
    ensure_organisation_ids_in_admin_scope,
    ensure_organisation_ids_in_tenant,
    ensure_user_in_tenant,
    get_current_user_manager,
    sync_user_role_fields,
    user_shares_administered_org,
)
from ..user_access import (
    administered_organisation_ids,
    can_manage_tenant,
    is_organisation_admin,
    is_platform_admin,
    is_tenant_admin,
    user_role,
)

router = APIRouter()

_EVENT_ADMIN_PIN_RE = re.compile(r"^\d{6}$")


def _raise_email_already_registered() -> None:
    raise api_error("email_already_registered", status.HTTP_400_BAD_REQUEST)


def _apply_event_admin_pin(user: User, pin: str | None, *, has_orgs: bool) -> None:
    if pin is None:
        return
    if pin == "":
        user.event_admin_pin_hash = None
        return
    if not _EVENT_ADMIN_PIN_RE.fullmatch(pin):
        raise api_error("event_admin_pin_digits", status.HTTP_400_BAD_REQUEST)
    if not has_orgs:
        raise api_error("event_admin_pin_requires_org", status.HTTP_400_BAD_REQUEST)
    user.event_admin_pin_hash = get_password_hash(pin)


class OrganisationLinkRead(BaseModel):
    id: int
    name: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    email: str
    role: str
    is_admin: bool
    hire_company_id: int | None = None
    has_event_admin_pin: bool = False
    organisation_ids: list[int] = []
    organisations: list[OrganisationLinkRead] = []


class UserCreate(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=1)
    role: str = ROLE_MEMBER
    hire_company_id: int | None = None
    organisation_ids: list[int] = Field(default_factory=list)
    event_admin_pin: str | None = Field(None, max_length=6)

    @field_validator("event_admin_pin")
    @classmethod
    def validate_event_admin_pin_create(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not _EVENT_ADMIN_PIN_RE.fullmatch(v):
            raise ValueError("event_admin_pin must be exactly 6 digits")
        return v

    @field_validator("role")
    @classmethod
    def validate_role_create(cls, v: str) -> str:
        if v not in ALL_ROLES:
            raise ValueError("Invalid role")
        return v


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    role: str | None = None
    hire_company_id: int | None = None
    organisation_ids: list[int] | None = None
    event_admin_pin: str | None = Field(None, max_length=6)

    @field_validator("event_admin_pin")
    @classmethod
    def validate_event_admin_pin_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v == "":
            return ""
        if not _EVENT_ADMIN_PIN_RE.fullmatch(v):
            raise ValueError("event_admin_pin must be exactly 6 digits")
        return v

    @field_validator("role")
    @classmethod
    def validate_role_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in ALL_ROLES:
            raise ValueError("Invalid role")
        return v


def user_to_read(u: User) -> dict:
    orgs = sorted(u.organisations or [], key=lambda o: (o.name or "").lower())
    role = user_role(u)
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": role,
        "is_admin": role == ROLE_PLATFORM_ADMIN,
        "hire_company_id": u.hire_company_id,
        "has_event_admin_pin": bool(getattr(u, "event_admin_pin_hash", None)),
        "organisation_ids": [o.id for o in orgs],
        "organisations": [{"id": o.id, "name": o.name} for o in orgs],
    }


def _assert_role_assignable_by_actor(role: str, acting_user: User) -> None:
    if is_organisation_admin(acting_user):
        if role not in ASSIGNABLE_BY_ORGANISATION_ADMIN:
            raise api_error("cannot_assign_role", status.HTTP_403_FORBIDDEN)
        return
    if role == ROLE_PLATFORM_ADMIN and not is_platform_admin(acting_user):
        raise api_error("cannot_assign_platform_admin", status.HTTP_403_FORBIDDEN)
    if role == ROLE_TENANT_ADMIN and not can_manage_tenant(acting_user):
        raise api_error("cannot_assign_role", status.HTTP_403_FORBIDDEN)


def _apply_role_on_create(
    db_user: User,
    role: str,
    hire_company_id: int | None,
    tenant_hire_company_id: int,
    acting_user: User,
) -> None:
    _assert_role_assignable_by_actor(role, acting_user)
    if role == ROLE_PLATFORM_ADMIN:
        db_user.role = ROLE_PLATFORM_ADMIN
        db_user.is_superuser = True
        db_user.hire_company_id = None
        return
    if role == ROLE_TENANT_ADMIN:
        db_user.role = ROLE_TENANT_ADMIN
        db_user.is_superuser = False
        db_user.hire_company_id = hire_company_id or tenant_hire_company_id
        if db_user.hire_company_id != tenant_hire_company_id:
            raise api_error("invalid_verleiher_for_tenant_admin", status.HTTP_400_BAD_REQUEST)
        return
    if role == ROLE_ORGANISATION_ADMIN:
        db_user.role = ROLE_ORGANISATION_ADMIN
        db_user.is_superuser = False
        db_user.hire_company_id = tenant_hire_company_id
        return
    db_user.role = ROLE_MEMBER
    db_user.is_superuser = False
    db_user.hire_company_id = tenant_hire_company_id


def _admin_org_ids(acting_user: User) -> list[int]:
    return administered_organisation_ids(acting_user)


def _ensure_actor_can_manage_target(acting_user: User, target: User) -> None:
    if can_manage_tenant(acting_user):
        return
    admin_org_ids = _admin_org_ids(acting_user)
    if not user_shares_administered_org(target, admin_org_ids):
        raise api_error("not_allowed_for_organisation", status.HTTP_403_FORBIDDEN)
    if is_tenant_admin(target) or user_role(target) == ROLE_PLATFORM_ADMIN:
        raise api_error("cannot_modify_elevated_user", status.HTTP_403_FORBIDDEN)


def _filter_users_for_organisation_admin(
    users: list[User],
    admin_org_ids: list[int],
) -> list[User]:
    return [u for u in users if user_shares_administered_org(u, admin_org_ids)]


@router.get("/", response_model=list[UserRead])
@limiter.limit(USERS_RATE_LIMIT)
def list_or_search_users(
    request: Request,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_user_manager),
):
    query = (
        db.query(User)
        .options(joinedload(User.organisations))
        .filter(
            or_(
                User.hire_company_id == tenant.hire_company_id,
                User.organisations.any(Organisation.hire_company_id == tenant.hire_company_id),
            )
        )
    )
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(User.email.ilike(term), User.name.ilike(term)))
    users = query.order_by(User.id).all()
    if is_organisation_admin(current_user):
        users = _filter_users_for_organisation_admin(users, _admin_org_ids(current_user))
    return [user_to_read(u) for u in users]


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(USERS_RATE_LIMIT)
def create_user(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_user_manager),
):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise api_error("email_already_registered", status.HTTP_400_BAD_REQUEST)
    if is_organisation_admin(current_user):
        ensure_organisation_ids_in_admin_scope(user_in.organisation_ids, _admin_org_ids(current_user))
    db_user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    _apply_role_on_create(db_user, user_in.role, user_in.hire_company_id, tenant.hire_company_id, current_user)
    db.add(db_user)
    db.flush()
    if user_in.organisation_ids:
        orgs = ensure_organisation_ids_in_tenant(db, user_in.organisation_ids, tenant.hire_company_id)
        if is_organisation_admin(current_user):
            ensure_organisation_ids_in_admin_scope(user_in.organisation_ids, _admin_org_ids(current_user))
        db_user.organisations = orgs
    elif is_organisation_admin(current_user):
        raise api_error("organisation_required_for_user", status.HTTP_400_BAD_REQUEST)
    _apply_event_admin_pin(
        db_user,
        user_in.event_admin_pin,
        has_orgs=bool(user_in.organisation_ids),
    )
    sync_user_role_fields(db_user)
    _ensure_home_verleiher(db_user, tenant.hire_company_id)
    commit_or_raise(db, on_integrity=_raise_email_already_registered)
    out = db.query(User).options(joinedload(User.organisations)).filter(User.id == db_user.id).first()
    return user_to_read(out)


def _ensure_home_verleiher(user: User, tenant_hire_company_id: int) -> None:
    """Fill home Verleiher for member / organisation_admin when missing (e.g. legacy rows)."""
    role = user_role(user)
    if role in (ROLE_MEMBER, ROLE_ORGANISATION_ADMIN) and user.hire_company_id is None:
        user.hire_company_id = tenant_hire_company_id


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_user_manager),
):
    u = ensure_user_in_tenant(
        db, user_id, tenant.hire_company_id, load_organisations=True
    )
    _ensure_actor_can_manage_target(current_user, u)
    if u.is_superuser and not is_platform_admin(current_user):
        raise api_error("cannot_modify_platform_admin", status.HTTP_403_FORBIDDEN)
    if user_in.email is not None and user_in.email != u.email:
        taken = db.query(User).filter(User.email == user_in.email).first()
        if taken:
            raise api_error("email_already_registered", status.HTTP_400_BAD_REQUEST)
        u.email = user_in.email
    if user_in.name is not None:
        u.name = user_in.name
    if user_in.role is not None:
        _assert_role_assignable_by_actor(user_in.role, current_user)
        _apply_role_on_create(u, user_in.role, user_in.hire_company_id, tenant.hire_company_id, current_user)
    elif user_in.hire_company_id is not None and user_role(u) == ROLE_TENANT_ADMIN:
        if not can_manage_tenant(current_user):
            raise api_error("cannot_assign_role", status.HTTP_403_FORBIDDEN)
        u.hire_company_id = user_in.hire_company_id
    if user_in.organisation_ids is not None:
        if is_organisation_admin(current_user):
            ensure_organisation_ids_in_admin_scope(user_in.organisation_ids, _admin_org_ids(current_user))
        orgs = ensure_organisation_ids_in_tenant(db, user_in.organisation_ids, tenant.hire_company_id)
        u.organisations = orgs
    update_data = user_in.model_dump(exclude_unset=True)
    if "event_admin_pin" in update_data:
        org_ids = (
            user_in.organisation_ids
            if user_in.organisation_ids is not None
            else [o.id for o in (u.organisations or [])]
        )
        _apply_event_admin_pin(u, update_data["event_admin_pin"], has_orgs=bool(org_ids))
    sync_user_role_fields(u)
    _ensure_home_verleiher(u, tenant.hire_company_id)
    commit_or_raise(db, on_integrity=_raise_email_already_registered)
    out = db.query(User).options(joinedload(User.organisations)).filter(User.id == user_id).first()
    return user_to_read(out)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_user_manager),
):
    u = ensure_user_in_tenant(db, user_id, tenant.hire_company_id, load_organisations=True)
    _ensure_actor_can_manage_target(current_user, u)
    if u.id == current_user.id:
        raise api_error("cannot_delete_own_account", status.HTTP_400_BAD_REQUEST)
    if u.is_superuser:
        other_super = db.query(User).filter(User.is_superuser.is_(True), User.id != u.id).first()
        if not other_super:
            raise api_error("cannot_delete_last_admin", status.HTTP_400_BAD_REQUEST)
    db.delete(u)
    commit_or_raise(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
