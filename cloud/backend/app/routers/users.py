import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..models import Organisation, User
from ..roles import ROLE_MEMBER, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN
from ..security import get_password_hash
from ..auth_deps import get_current_user
from ..deps import get_db
from ..tenancy import (
    TenantContext,
    ensure_organisation_ids_in_tenant,
    get_current_tenant_admin,
    sync_user_role_fields,
)
from ..user_access import is_platform_admin, user_role

router = APIRouter()

_EVENT_ADMIN_PIN_RE = re.compile(r"^\d{6}$")


def _apply_event_admin_pin(user: User, pin: str | None, *, has_orgs: bool) -> None:
    if pin is None:
        return
    if pin == "":
        user.event_admin_pin_hash = None
        return
    if not _EVENT_ADMIN_PIN_RE.fullmatch(pin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_admin_pin must be exactly 6 digits",
        )
    if not has_orgs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_admin_pin requires at least one organisation",
        )
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
    organisation_ids: List[int] = []
    organisations: List[OrganisationLinkRead] = []


class UserCreate(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=1)
    role: str = ROLE_MEMBER
    hire_company_id: int | None = None
    organisation_ids: List[int] = Field(default_factory=list)
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
        if v not in (ROLE_MEMBER, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN):
            raise ValueError("Invalid role")
        return v


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    role: str | None = None
    hire_company_id: int | None = None
    organisation_ids: List[int] | None = None
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
        if v not in (ROLE_MEMBER, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN):
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


def _apply_role_on_create(
    db_user: User,
    role: str,
    hire_company_id: int | None,
    tenant_hire_company_id: int,
    acting_user: User,
) -> None:
    if role == ROLE_PLATFORM_ADMIN:
        if not is_platform_admin(acting_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create platform administrators")
        db_user.role = ROLE_PLATFORM_ADMIN
        db_user.is_superuser = True
        db_user.hire_company_id = None
        return
    if role == ROLE_ORG_ADMIN:
        db_user.role = ROLE_ORG_ADMIN
        db_user.is_superuser = False
        db_user.hire_company_id = hire_company_id or tenant_hire_company_id
        if db_user.hire_company_id != tenant_hire_company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Verleiher for org admin")
        return
    db_user.role = ROLE_MEMBER
    db_user.is_superuser = False
    db_user.hire_company_id = None


@router.get("/", response_model=List[UserRead])
def list_or_search_users(
    q: str | None = None,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
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
    return [user_to_read(u) for u in users]


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
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
        db_user.organisations = orgs
    _apply_event_admin_pin(
        db_user,
        user_in.event_admin_pin,
        has_orgs=bool(user_in.organisation_ids),
    )
    sync_user_role_fields(db_user)
    db.commit()
    out = db.query(User).options(joinedload(User.organisations)).filter(User.id == db_user.id).first()
    return user_to_read(out)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    u = (
        db.query(User)
        .options(joinedload(User.organisations))
        .filter(User.id == user_id)
        .first()
    )
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if u.is_superuser and not is_platform_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify platform administrators")
    if u.hire_company_id and u.hire_company_id != tenant.hire_company_id:
        if not any(o.hire_company_id == tenant.hire_company_id for o in (u.organisations or [])):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not in this Verleiher")
    if user_in.email is not None and user_in.email != u.email:
        taken = db.query(User).filter(User.email == user_in.email).first()
        if taken:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        u.email = user_in.email
    if user_in.name is not None:
        u.name = user_in.name
    if user_in.role is not None:
        if user_in.role == ROLE_PLATFORM_ADMIN and not is_platform_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign platform administrator")
        _apply_role_on_create(u, user_in.role, user_in.hire_company_id, tenant.hire_company_id, current_user)
    elif user_in.hire_company_id is not None and user_role(u) == ROLE_ORG_ADMIN:
        u.hire_company_id = user_in.hire_company_id
    if user_in.organisation_ids is not None:
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
    db.commit()
    out = db.query(User).options(joinedload(User.organisations)).filter(User.id == user_id).first()
    return user_to_read(out)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if u.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
    if u.is_superuser:
        other_super = db.query(User).filter(User.is_superuser.is_(True), User.id != u.id).first()
        if not other_super:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last administrator",
            )
    db.delete(u)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
