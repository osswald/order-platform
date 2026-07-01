"""Organisation color palette for app layout buttons."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..color_palette_config import (
    ColorPaletteRead,
    ColorPaletteUpdate,
    apply_color_palette_update,
    read_color_palette_response,
)
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..models import Organisation, User
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    ensure_user_can_use_organisation,
    get_current_tenant,
)

router = APIRouter()


def _ensure_org_access(
    db: Session,
    organisation_id: int,
    user: User,
    tenant: TenantContext,
    *,
    manage: bool = False,
) -> Organisation:
    if manage:
        ensure_can_manage_organisation(user, organisation_id)
    else:
        ensure_user_can_use_organisation(db, user, organisation_id, tenant.hire_company_id)
    return ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)


@router.get(
    "/organisations/{organisation_id}/color-palette",
    response_model=ColorPaletteRead,
)
def get_color_palette(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    org = _ensure_org_access(db, organisation_id, current_user, tenant)
    return read_color_palette_response(org)


@router.put(
    "/organisations/{organisation_id}/color-palette",
    response_model=ColorPaletteRead,
)
def put_color_palette(
    organisation_id: int,
    body: ColorPaletteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    org = _ensure_org_access(db, organisation_id, current_user, tenant, manage=True)
    apply_color_palette_update(org, body)
    commit_or_raise(db)
    db.refresh(org)
    return read_color_palette_response(org)
