"""Organisation-level preset comments for order positions."""


from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import Organisation, OrganisationPositionComment, User
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    ensure_user_can_use_organisation,
    get_current_tenant,
)

router = APIRouter()


class PositionCommentPresetBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=512)
    sort_order: int = 0


class PositionCommentPresetCreate(PositionCommentPresetBase):
    pass


class PositionCommentPresetUpdate(BaseModel):
    text: str | None = Field(None, min_length=1, max_length=512)
    sort_order: int | None = None


class PositionCommentPresetRead(PositionCommentPresetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_id: int


def _preset_response(row: OrganisationPositionComment) -> dict:
    return {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "text": row.text,
        "sort_order": row.sort_order,
    }


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
    "/organisations/{organisation_id}/position-comments",
    response_model=list[PositionCommentPresetRead],
)
def list_position_comments(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    _ensure_org_access(db, organisation_id, current_user, tenant)
    rows = (
        db.query(OrganisationPositionComment)
        .filter(OrganisationPositionComment.organisation_id == organisation_id)
        .order_by(OrganisationPositionComment.sort_order, OrganisationPositionComment.id)
        .all()
    )
    return [_preset_response(row) for row in rows]


@router.post(
    "/organisations/{organisation_id}/position-comments",
    response_model=PositionCommentPresetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_position_comment(
    organisation_id: int,
    body: PositionCommentPresetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    _ensure_org_access(db, organisation_id, current_user, tenant, manage=True)
    row = OrganisationPositionComment(
        organisation_id=organisation_id,
        text=body.text.strip(),
        sort_order=body.sort_order,
    )
    db.add(row)
    commit_or_raise(db)
    db.refresh(row)
    return _preset_response(row)


@router.put(
    "/organisations/{organisation_id}/position-comments/{preset_id}",
    response_model=PositionCommentPresetRead,
)
def update_position_comment(
    organisation_id: int,
    preset_id: int,
    body: PositionCommentPresetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    _ensure_org_access(db, organisation_id, current_user, tenant, manage=True)
    row = (
        db.query(OrganisationPositionComment)
        .filter(
            OrganisationPositionComment.id == preset_id,
            OrganisationPositionComment.organisation_id == organisation_id,
        )
        .first()
    )
    if not row:
        raise api_error("position_comment_not_found", status.HTTP_404_NOT_FOUND)
    if body.text is not None:
        row.text = body.text.strip()
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    commit_or_raise(db)
    db.refresh(row)
    return _preset_response(row)


@router.delete(
    "/organisations/{organisation_id}/position-comments/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_position_comment(
    organisation_id: int,
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    _ensure_org_access(db, organisation_id, current_user, tenant, manage=True)
    row = (
        db.query(OrganisationPositionComment)
        .filter(
            OrganisationPositionComment.id == preset_id,
            OrganisationPositionComment.organisation_id == organisation_id,
        )
        .first()
    )
    if not row:
        raise api_error("position_comment_not_found", status.HTTP_404_NOT_FOUND)
    db.delete(row)
    commit_or_raise(db)
    return None
