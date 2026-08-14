"""Organisation screensaver gallery admin and edge download endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import OrganisationScreensaverImage, User
from ..screensaver_gallery import (
    delete_screensaver_image,
    get_by_sha256,
    image_to_read_dict,
    list_screensaver_images,
    screensaver_image_bytes,
    store_screensaver_image,
)
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    get_current_tenant,
)
from .edge import ApplianceEdgeContext, get_edge_server_appliance

router = APIRouter()


class ScreensaverImageRead(BaseModel):
    id: int
    sha256: str
    mime: str
    created_at: datetime | None = None


@router.get(
    "/organisations/{organisation_id}/screensaver-images",
    response_model=list[ScreensaverImageRead],
)
def list_organisation_screensaver_images(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    rows = list_screensaver_images(db, organisation_id)
    return [ScreensaverImageRead(**image_to_read_dict(row)) for row in rows]


@router.post(
    "/organisations/{organisation_id}/screensaver-images",
    response_model=ScreensaverImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_organisation_screensaver_image(
    organisation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    raw = await file.read()
    try:
        row = store_screensaver_image(db, org, mime, raw)
    except ValueError as e:
        raise api_error("validation_failed", status.HTTP_400_BAD_REQUEST) from e
    commit_or_raise(db)
    db.refresh(row)
    return ScreensaverImageRead(**image_to_read_dict(row))


@router.get("/organisations/{organisation_id}/screensaver-images/{image_id}")
def get_organisation_screensaver_image(
    organisation_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    row = (
        db.query(OrganisationScreensaverImage)
        .filter(
            OrganisationScreensaverImage.organisation_id == organisation_id,
            OrganisationScreensaverImage.id == image_id,
        )
        .first()
    )
    if row is None:
        raise api_error("screensaver_image_not_found", status.HTTP_404_NOT_FOUND)
    mime, raw = screensaver_image_bytes(row)
    return Response(content=raw, media_type=mime)


@router.delete(
    "/organisations/{organisation_id}/screensaver-images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organisation_screensaver_image(
    organisation_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    if not delete_screensaver_image(db, organisation_id, image_id):
        raise api_error("screensaver_image_not_found", status.HTTP_404_NOT_FOUND)
    commit_or_raise(db)


@router.get("/edge/v1/screensaver/{sha256}")
def download_edge_screensaver_image(
    sha256: str,
    ctx: ApplianceEdgeContext = Depends(get_edge_server_appliance),
    db: Session = Depends(get_db),
):
    digest = (sha256 or "").strip().lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise api_error("screensaver_image_not_found", status.HTTP_404_NOT_FOUND)
    row = get_by_sha256(db, ctx.organisation_id, digest)
    if row is None:
        raise api_error("screensaver_image_not_found", status.HTTP_404_NOT_FOUND)
    mime, raw = screensaver_image_bytes(row)
    return Response(content=raw, media_type=mime)
