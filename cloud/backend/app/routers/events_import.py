"""Orderjutsu event import routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import User
from ..orderjutsu_import import OjImportError, build_preview, commit_orderjutsu_import
from ..schemas.orderjutsu_import import (
    OrderjutsuImportCommit,
    OrderjutsuImportCommitResult,
    OrderjutsuImportPreview,
    OrderjutsuImportPreviewRequest,
)
from ..tenancy import (
    TenantContext,
    ensure_user_can_use_organisation,
    get_current_organisation_manager,
)
from .events_helpers import event_response, get_event_for_configuration, serialize_event_configuration

router = APIRouter()


@router.post("/import/orderjutsu/preview", response_model=OrderjutsuImportPreview)
def preview_orderjutsu_import(
    body: OrderjutsuImportPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_organisation_manager),
):
    ensure_user_can_use_organisation(db, current_user, body.organisation_id, tenant.hire_company_id)
    try:
        return build_preview(db, organisation_id=body.organisation_id, payload=body.payload)
    except OjImportError as exc:
        raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/import/orderjutsu/commit", response_model=OrderjutsuImportCommitResult)
def commit_orderjutsu_import_endpoint(
    body: OrderjutsuImportCommit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_organisation_manager),
):
    ensure_user_can_use_organisation(db, current_user, body.organisation_id, tenant.hire_company_id)
    payload = body.payload
    try:
        event = commit_orderjutsu_import(db, body, payload)
        commit_or_raise(db)
    except OjImportError as exc:
        db.rollback()
        raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    loaded = get_event_for_configuration(db, current_user, event.id, tenant.hire_company_id)
    return OrderjutsuImportCommitResult(
        event_id=event.id,
        event=event_response(loaded),
        configuration=serialize_event_configuration(db, loaded),
    )
