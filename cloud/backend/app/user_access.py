from .models import User
from .roles import ROLE_MEMBER, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN


def user_role(user: User) -> str:
    role = getattr(user, "role", None) or ROLE_MEMBER
    if user.is_superuser and role == ROLE_MEMBER:
        return ROLE_PLATFORM_ADMIN
    return role


def is_platform_admin(user: User) -> bool:
    return user.is_superuser or user_role(user) == ROLE_PLATFORM_ADMIN


def is_org_admin(user: User) -> bool:
    return user_role(user) == ROLE_ORG_ADMIN


def can_manage_tenant(user: User) -> bool:
    return is_platform_admin(user) or is_org_admin(user)


def user_hire_company_id(user: User) -> int | None:
    if is_org_admin(user):
        return user.hire_company_id
    return None
