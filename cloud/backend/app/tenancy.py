"""Tenant (Verleiher / hire company) scoping for cloud API."""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .deps import get_db
from .models import Event, HireCompany, Organisation, User
from .user_access import (
    can_manage_tenant,
    is_org_admin,
    is_platform_admin,
    user_hire_company_id,
)
from .auth_deps import get_current_user

HIRE_COMPANY_HEADER = "x-hire-company-id"


@dataclass
class TenantContext:
    hire_company_id: int
    hire_company: HireCompany | None = None


def resolve_hire_company_id(
    user: User,
    header_hire_company_id: int | None,
) -> int:
    if is_org_admin(user):
        if user.hire_company_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organisation admin has no Verleiher assigned",
            )
        return user.hire_company_id
    if is_platform_admin(user):
        if header_hire_company_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Hire-Company-Id header required for platform administrators",
            )
        return header_hire_company_id
    if user.hire_company_id is not None:
        return user.hire_company_id
    orgs = user.organisations or []
    if not orgs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active Verleiher context could not be determined",
        )
    tenant_ids = {o.hire_company_id for o in orgs}
    if len(tenant_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is linked to multiple Verleiher; contact an administrator",
        )
    return next(iter(tenant_ids))


def get_tenant_context(
    db: Session,
    user: User,
    header_hire_company_id: int | None,
) -> TenantContext:
    hire_company_id = resolve_hire_company_id(user, header_hire_company_id)
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verleiher not found")
    if is_org_admin(user) and user.hire_company_id != hire_company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this Verleiher")
    if is_platform_admin(user) and header_hire_company_id is not None and header_hire_company_id != hire_company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this Verleiher")
    return TenantContext(hire_company_id=hire_company_id, hire_company=company)


def parse_hire_company_header(
    x_hire_company_id: str | None = Header(default=None, alias="X-Hire-Company-Id"),
) -> int | None:
    if x_hire_company_id is None or x_hire_company_id.strip() == "":
        return None
    try:
        return int(x_hire_company_id.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Hire-Company-Id",
        ) from exc


def get_current_tenant(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    header_hire_company_id: int | None = Depends(parse_hire_company_header),
) -> TenantContext:
    return get_tenant_context(db, current_user, header_hire_company_id)


def get_current_tenant_admin(
    tenant: TenantContext = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> TenantContext:
    if not can_manage_tenant(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires Verleiher administrator privileges",
        )
    return tenant


def get_current_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_platform_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires platform administrator privileges",
        )
    return current_user


def ensure_org_in_tenant(db: Session, organisation_id: int, hire_company_id: int) -> Organisation:
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    if org.hire_company_id != hire_company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation not in this Verleiher")
    return org


def readable_organisations(
    db: Session,
    current_user: User,
    hire_company_id: int,
) -> list[Organisation]:
    if can_manage_tenant(current_user):
        return (
            db.query(Organisation)
            .filter(Organisation.hire_company_id == hire_company_id)
            .order_by(Organisation.name)
            .all()
        )
    linked = [o for o in (current_user.organisations or []) if o.hire_company_id == hire_company_id]
    return sorted(linked, key=lambda org: org.name.lower())


def readable_events_query(db: Session, current_user: User, hire_company_id: int):
    query = (
        db.query(Event)
        .join(Event.organisation)
        .filter(Organisation.hire_company_id == hire_company_id)
    )
    if can_manage_tenant(current_user):
        return query
    return (
        query.join(Organisation.users)
        .filter(User.id == current_user.id)
    )


def ensure_user_can_use_organisation(
    db: Session,
    current_user: User,
    organisation_id: int | None,
    hire_company_id: int,
) -> Organisation:
    organisations = readable_organisations(db, current_user, hire_company_id)
    if organisation_id is None:
        if len(organisations) == 1:
            return organisations[0]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organisation is required when the user is linked to multiple organisations",
        )
    organisation = ensure_org_in_tenant(db, organisation_id, hire_company_id)
    if can_manage_tenant(current_user):
        return organisation
    if not any(org.id == organisation.id for org in organisations):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this organisation")
    return organisation


def user_belongs_to_tenant(user: User, hire_company_id: int) -> bool:
    if user.hire_company_id == hire_company_id:
        return True
    return any(o.hire_company_id == hire_company_id for o in (user.organisations or []))


def get_user_in_tenant(
    db: Session,
    user_id: int,
    hire_company_id: int,
    *,
    load_organisations: bool = False,
) -> User | None:
    query = db.query(User).filter(User.id == user_id).filter(
        or_(
            User.hire_company_id == hire_company_id,
            User.organisations.any(Organisation.hire_company_id == hire_company_id),
        )
    )
    if load_organisations:
        query = query.options(joinedload(User.organisations))
    return query.first()


def ensure_user_in_tenant(
    db: Session,
    user_id: int,
    hire_company_id: int,
    *,
    load_organisations: bool = False,
) -> User:
    user = get_user_in_tenant(
        db, user_id, hire_company_id, load_organisations=load_organisations
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def ensure_users_in_tenant(
    db: Session,
    user_ids: list[int],
    hire_company_id: int,
) -> list[User]:
    if not user_ids:
        return []
    users = (
        db.query(User)
        .options(joinedload(User.organisations))
        .filter(User.id.in_(user_ids))
        .all()
    )
    found = {u.id for u in users}
    missing = set(user_ids) - found
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown user id(s)")
    for user in users:
        if not user_belongs_to_tenant(user, hire_company_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User belongs to another Verleiher",
            )
    return users


def ensure_organisation_ids_in_tenant(
    db: Session,
    organisation_ids: list[int],
    hire_company_id: int,
) -> list[Organisation]:
    if not organisation_ids:
        return []
    orgs = db.query(Organisation).filter(Organisation.id.in_(organisation_ids)).all()
    found = {o.id for o in orgs}
    missing = set(organisation_ids) - found
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown organisation id(s)")
    for org in orgs:
        if org.hire_company_id != hire_company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisation belongs to another Verleiher",
            )
    return orgs


def sync_user_role_fields(user: User) -> None:
    from .roles import ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN
    from .user_access import user_role

    role = user_role(user)
    user.role = role
    if role == ROLE_PLATFORM_ADMIN:
        user.is_superuser = True
        user.hire_company_id = None
    elif role == ROLE_ORG_ADMIN:
        user.is_superuser = False
    else:
        user.is_superuser = False
        user.hire_company_id = None
