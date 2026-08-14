"""Cloud-admin SumUp Solo reader management for an organisation."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .. import sumup_client
from ..auth_deps import get_current_user
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import Organisation, SumupReader, User
from ..sumup_client import normalize_pairing_code, sumup_error
from ..sumup_tokens import get_valid_access_token
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    get_current_tenant,
)

router = APIRouter()


class SumupReaderResponse(BaseModel):
    id: int
    organisation_id: int
    sumup_reader_id: str
    label: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SumupReaderCreateRequest(BaseModel):
    pairing_code: str = Field(..., min_length=8, max_length=20)
    label: str = Field(..., min_length=1, max_length=128)

    @field_validator("pairing_code")
    @classmethod
    def _normalize_pairing_code(cls, value: str) -> str:
        code = normalize_pairing_code(value)
        if not (8 <= len(code) <= 9) or not code.isalnum():
            raise ValueError("pairing_code must be 8–9 alphanumeric characters")
        return code


class SumupReaderUpdateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=128)


def _reader_response(reader: SumupReader) -> SumupReaderResponse:
    return SumupReaderResponse(
        id=reader.id,
        organisation_id=reader.organisation_id,
        sumup_reader_id=reader.sumup_reader_id,
        label=reader.label,
        status=reader.status,
        created_at=reader.created_at,
        updated_at=reader.updated_at,
    )


def _require_connected_org(db: Session, organisation: Organisation) -> None:
    # API-key connect stores access_token without refresh_token; OAuth has both.
    if not organisation.sumup_merchant_code or not organisation.sumup_access_token:
        raise api_error("validation_failed", status.HTTP_409_CONFLICT)


def _sync_reader_statuses_from_sumup(
    db: Session,
    organisation: Organisation,
    readers: list[SumupReader],
) -> None:
    """Refresh persisted pairing status from SumUp's merchant reader list."""
    if not readers or not organisation.sumup_merchant_code:
        return
    try:
        access_token = get_valid_access_token(db, organisation)
        remote = sumup_client.list_readers(access_token, organisation.sumup_merchant_code)
    except (sumup_client.SumupConfigError, sumup_client.SumupApiError):
        # Keep local snapshots if SumUp is unreachable; list still works offline.
        return

    by_id: dict[str, str] = {}
    for item in remote:
        reader_id = item.get("id")
        remote_status = item.get("status")
        if isinstance(reader_id, str) and reader_id and isinstance(remote_status, str) and remote_status:
            by_id[reader_id] = remote_status

    dirty = False
    for reader in readers:
        remote_status = by_id.get(reader.sumup_reader_id)
        if remote_status and remote_status != reader.status:
            reader.status = remote_status
            dirty = True
    if dirty:
        commit_or_raise(db)


@router.get("/organisations/{organisation_id}/readers", response_model=list[SumupReaderResponse])
def list_org_readers(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[SumupReaderResponse]:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    readers = (
        db.query(SumupReader)
        .filter(SumupReader.organisation_id == organisation.id)
        .order_by(SumupReader.label)
        .all()
    )
    if organisation.sumup_merchant_code and organisation.sumup_access_token:
        _sync_reader_statuses_from_sumup(db, organisation, readers)
    return [_reader_response(reader) for reader in readers]


@router.post(
    "/organisations/{organisation_id}/readers",
    response_model=SumupReaderResponse,
    status_code=status.HTTP_201_CREATED,
)
def pair_reader(
    organisation_id: int,
    body: SumupReaderCreateRequest,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupReaderResponse:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    _require_connected_org(db, organisation)

    try:
        access_token = get_valid_access_token(db, organisation)
        created = sumup_client.create_reader(
            access_token,
            organisation.sumup_merchant_code,
            body.pairing_code,
            body.label.strip(),
        )
    except (sumup_client.SumupConfigError, sumup_client.SumupApiError) as exc:
        raise sumup_error(exc) from exc

    sumup_reader_id = created.get("id")
    if not sumup_reader_id:
        raise sumup_error(sumup_client.SumupApiError(502, "SumUp create reader missing id"))

    reader = SumupReader(
        organisation_id=organisation.id,
        sumup_reader_id=sumup_reader_id,
        label=body.label.strip(),
        status=str(created.get("status") or "paired"),
    )
    db.add(reader)
    commit_or_raise(db)
    db.refresh(reader)
    return _reader_response(reader)


@router.patch("/organisations/{organisation_id}/readers/{reader_id}", response_model=SumupReaderResponse)
def rename_reader(
    organisation_id: int,
    reader_id: int,
    body: SumupReaderUpdateRequest,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupReaderResponse:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    _require_connected_org(db, organisation)

    reader = (
        db.query(SumupReader)
        .filter(SumupReader.id == reader_id, SumupReader.organisation_id == organisation.id)
        .first()
    )
    if not reader:
        raise api_error("validation_failed", status.HTTP_404_NOT_FOUND)

    try:
        access_token = get_valid_access_token(db, organisation)
        updated = sumup_client.update_reader(
            access_token,
            organisation.sumup_merchant_code,
            reader.sumup_reader_id,
            body.label.strip(),
        )
    except (sumup_client.SumupConfigError, sumup_client.SumupApiError) as exc:
        raise sumup_error(exc) from exc

    reader.label = body.label.strip()
    if updated.get("status"):
        reader.status = str(updated["status"])
    commit_or_raise(db)
    db.refresh(reader)
    return _reader_response(reader)


@router.delete("/organisations/{organisation_id}/readers/{reader_id}", status_code=status.HTTP_204_NO_CONTENT)
def unpair_reader(
    organisation_id: int,
    reader_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    _require_connected_org(db, organisation)

    reader = (
        db.query(SumupReader)
        .filter(SumupReader.id == reader_id, SumupReader.organisation_id == organisation.id)
        .first()
    )
    if not reader:
        raise api_error("validation_failed", status.HTTP_404_NOT_FOUND)

    try:
        access_token = get_valid_access_token(db, organisation)
        sumup_client.delete_reader(
            access_token,
            organisation.sumup_merchant_code,
            reader.sumup_reader_id,
        )
    except (sumup_client.SumupConfigError, sumup_client.SumupApiError) as exc:
        raise sumup_error(exc) from exc

    db.delete(reader)
    commit_or_raise(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
