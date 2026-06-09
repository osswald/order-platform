"""Tenant (Verleiher / hire company) scoping for cloud API."""

from dataclasses import dataclass

from fastapi import Depends, Header, status
from .i18n.errors import api_error
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
            raise api_error("org_admin_no_verleiher", status.HTTP_403_FORBIDDEN)
        return user.hire_company_id
    if is_platform_admin(user):
        if header_hire_company_id is None:
            raise api_error("hire_company_header_required", status.HTTP_400_BAD_REQUEST)
        return header_hire_company_id
    if user.hire_company_id is not None:
        return user.hire_company_id
    orgs = user.organisations or []
    if not orgs:
        raise api_error("verleiher_context_undetermined", status.HTTP_400_BAD_REQUEST)
    tenant_ids = {o.hire_company_id for o in orgs}
    if len(tenant_ids) != 1:
        raise api_error("user_multiple_verleiher", status.HTTP_400_BAD_REQUEST)
    return next(iter(tenant_ids))


def get_tenant_context(
    db: Session,
    user: User,
    header_hire_company_id: int | None,
) -> TenantContext:
    hire_company_id = resolve_hire_company_id(user, header_hire_company_id)
    company = db.query(HireCompany).filter(HireCompany.id == hire_company_id).first()
    if not company:
        raise api_error("verleiher_not_found", status.HTTP_404_NOT_FOUND)
    if is_org_admin(user) and user.hire_company_id != hire_company_id:
        raise api_error("not_allowed_for_verleiher", status.HTTP_403_FORBIDDEN)
    if is_platform_admin(user) and header_hire_company_id is not None and header_hire_company_id != hire_company_id:
        raise api_error("not_allowed_for_verleiher", status.HTTP_403_FORBIDDEN)
    return TenantContext(hire_company_id=hire_company_id, hire_company=company)


def parse_hire_company_header(
    x_hire_company_id: str | None = Header(default=None, alias="X-Hire-Company-Id"),
) -> int | None:
    if x_hire_company_id is None or x_hire_company_id.strip() == "":
        return None
    try:
        return int(x_hire_company_id.strip())
    except ValueError as exc:
        raise api_error("invalid_hire_company_id", status.HTTP_400_BAD_REQUEST) from exc


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
        raise api_error("requires_verleiher_admin", status.HTTP_403_FORBIDDEN)
    return tenant


def get_current_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_platform_admin(current_user):
        raise api_error("requires_platform_admin", status.HTTP_403_FORBIDDEN)
    return current_user


def ensure_org_in_tenant(db: Session, organisation_id: int, hire_company_id: int) -> Organisation:
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise api_error("organisation_not_found", status.HTTP_404_NOT_FOUND)
    if org.hire_company_id != hire_company_id:
        raise api_error("organisation_not_in_verleiher", status.HTTP_403_FORBIDDEN)
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
        raise api_error("organisation_required_multi", status.HTTP_422_UNPROCESSABLE_ENTITY)
    organisation = ensure_org_in_tenant(db, organisation_id, hire_company_id)
    if can_manage_tenant(current_user):
        return organisation
    if not any(org.id == organisation.id for org in organisations):
        raise api_error("not_allowed_for_organisation", status.HTTP_403_FORBIDDEN)
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
        raise api_error("user_not_found", status.HTTP_404_NOT_FOUND)
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
        raise api_error("unknown_user_ids", status.HTTP_400_BAD_REQUEST)
    for user in users:
        if not user_belongs_to_tenant(user, hire_company_id):
            raise api_error("user_wrong_verleiher", status.HTTP_400_BAD_REQUEST)
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
        raise api_error("unknown_organisation_ids", status.HTTP_400_BAD_REQUEST)
    for org in orgs:
        if org.hire_company_id != hire_company_id:
            raise api_error("organisation_wrong_verleiher", status.HTTP_400_BAD_REQUEST)
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
