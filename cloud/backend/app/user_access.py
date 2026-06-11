from .models import User
from .roles import (
    ROLE_MEMBER,
    ROLE_ORGANISATION_ADMIN,
    ROLE_PLATFORM_ADMIN,
    ROLE_TENANT_ADMIN,
)


def user_role(user: User) -> str:
    role = getattr(user, "role", None) or ROLE_MEMBER
    if user.is_superuser and role == ROLE_MEMBER:
        return ROLE_PLATFORM_ADMIN
    return role


def is_platform_admin(user: User) -> bool:
    return user.is_superuser or user_role(user) == ROLE_PLATFORM_ADMIN


def is_tenant_admin(user: User) -> bool:
    return user_role(user) == ROLE_TENANT_ADMIN


def is_organisation_admin(user: User) -> bool:
    return user_role(user) == ROLE_ORGANISATION_ADMIN


def can_manage_tenant(user: User) -> bool:
    return is_platform_admin(user) or is_tenant_admin(user)


def administered_organisation_ids(user: User) -> list[int]:
    if not is_organisation_admin(user):
        return []
    return [o.id for o in (user.organisations or [])]


def can_manage_organisation(user: User, organisation_id: int) -> bool:
    if can_manage_tenant(user):
        return True
    return organisation_id in administered_organisation_ids(user)


def user_hire_company_id(user: User) -> int | None:
    if is_tenant_admin(user):
        return user.hire_company_id
    return None
