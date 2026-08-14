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
from ..models import Event, EventCashRegister, Organisation, SumupReader, User
from ..sumup_checkout_state import unwrap_sumup_data
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
    device_identifier: str | None = None
    device_model: str | None = None
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


class SumupReaderTelemetryResponse(BaseModel):
    id: int
    sumup_reader_id: str
    label: str
    device_identifier: str | None = None
    device_model: str | None = None
    telemetry_available: bool
    online_status: str | None = None
    battery_level: float | None = None
    connection_type: str | None = None
    firmware_version: str | None = None
    last_activity: str | None = None
    state: str | None = None


def _reader_response(reader: SumupReader) -> SumupReaderResponse:
    return SumupReaderResponse(
        id=reader.id,
        organisation_id=reader.organisation_id,
        sumup_reader_id=reader.sumup_reader_id,
        label=reader.label,
        status=reader.status,
        device_identifier=reader.device_identifier,
        device_model=reader.device_model,
        created_at=reader.created_at,
        updated_at=reader.updated_at,
    )


def _require_connected_org(db: Session, organisation: Organisation) -> None:
    # API-key connect stores access_token without refresh_token; OAuth has both.
    if not organisation.sumup_merchant_code or not organisation.sumup_access_token:
        raise api_error("validation_failed", status.HTTP_409_CONFLICT)


def _clip(value: str | None, max_len: int) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    return trimmed[:max_len]


def _device_field(item: dict, key: str, max_len: int) -> str | None:
    device = item.get("device")
    if not isinstance(device, dict):
        return None
    raw = device.get(key)
    if not isinstance(raw, str):
        return None
    return _clip(raw, max_len)


def _label_from_remote(item: dict) -> str:
    name = item.get("name")
    if isinstance(name, str):
        clipped = _clip(name, 128)
        if clipped:
            return clipped
    serial = _device_field(item, "identifier", 128)
    if serial:
        return serial
    return "Solo"


def _clear_register_bindings(db: Session, organisation_id: int, reader_ids: list[str]) -> None:
    if not reader_ids:
        return
    event_ids = db.query(Event.id).filter(Event.organisation_id == organisation_id)
    (
        db.query(EventCashRegister)
        .filter(
            EventCashRegister.event_id.in_(event_ids),
            EventCashRegister.sumup_reader_id.in_(reader_ids),
        )
        .update({EventCashRegister.sumup_reader_id: None}, synchronize_session=False)
    )


def sync_reader_catalog(db: Session, organisation: Organisation) -> None:
    """Import, refresh, and prune local readers from SumUp's merchant catalog.

    No-op when SumUp is unreachable or the list payload is not well-formed.
    """
    if not organisation.sumup_merchant_code or not organisation.sumup_access_token:
        return
    try:
        access_token = get_valid_access_token(db, organisation)
        remote = sumup_client.list_readers(access_token, organisation.sumup_merchant_code)
    except (sumup_client.SumupConfigError, sumup_client.SumupApiError):
        return

    by_id: dict[str, dict] = {}
    for item in remote:
        if not isinstance(item, dict):
            continue
        reader_id = item.get("id")
        if isinstance(reader_id, str) and reader_id.strip():
            by_id[reader_id.strip()] = item

    local_readers = (
        db.query(SumupReader).filter(SumupReader.organisation_id == organisation.id).all()
    )
    local_by_id = {row.sumup_reader_id: row for row in local_readers}

    for reader_id, item in by_id.items():
        remote_status = item.get("status")
        status_value = remote_status.strip() if isinstance(remote_status, str) and remote_status.strip() else "paired"
        identifier = _device_field(item, "identifier", 128)
        model = _device_field(item, "model", 64)
        existing = local_by_id.get(reader_id)
        if existing is None:
            db.add(
                SumupReader(
                    organisation_id=organisation.id,
                    sumup_reader_id=reader_id,
                    label=_label_from_remote(item),
                    status=status_value,
                    device_identifier=identifier,
                    device_model=model,
                )
            )
            continue
        if existing.status != status_value:
            existing.status = status_value
        if identifier and existing.device_identifier != identifier:
            existing.device_identifier = identifier
        if model and existing.device_model != model:
            existing.device_model = model

    missing_ids = [reader_id for reader_id in local_by_id if reader_id not in by_id]
    for reader_id in missing_ids:
        db.delete(local_by_id[reader_id])
    _clear_register_bindings(db, organisation.id, missing_ids)
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
    if organisation.sumup_merchant_code and organisation.sumup_access_token:
        sync_reader_catalog(db, organisation)
    readers = (
        db.query(SumupReader)
        .filter(SumupReader.organisation_id == organisation.id)
        .order_by(SumupReader.label)
        .all()
    )
    return [_reader_response(reader) for reader in readers]


def _org_reader(db: Session, organisation: Organisation, reader_id: int) -> SumupReader | None:
    return (
        db.query(SumupReader)
        .filter(SumupReader.id == reader_id, SumupReader.organisation_id == organisation.id)
        .first()
    )


def _telemetry_identity(reader: SumupReader, *, available: bool) -> SumupReaderTelemetryResponse:
    return SumupReaderTelemetryResponse(
        id=reader.id,
        sumup_reader_id=reader.sumup_reader_id,
        label=reader.label,
        device_identifier=reader.device_identifier,
        device_model=reader.device_model,
        telemetry_available=available,
    )


@router.get(
    "/organisations/{organisation_id}/readers/{reader_id}/telemetry",
    response_model=SumupReaderTelemetryResponse,
)
def read_reader_telemetry(
    organisation_id: int,
    reader_id: int,
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SumupReaderTelemetryResponse:
    ensure_can_manage_organisation(current_user, organisation_id)
    organisation = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    _require_connected_org(db, organisation)
    reader = _org_reader(db, organisation, reader_id)
    if not reader:
        raise api_error("validation_failed", status.HTTP_404_NOT_FOUND)

    try:
        access_token = get_valid_access_token(db, organisation)
        payload = sumup_client.get_reader_status(
            access_token,
            organisation.sumup_merchant_code,
            reader.sumup_reader_id,
        )
    except (sumup_client.SumupConfigError, sumup_client.SumupApiError):
        return _telemetry_identity(reader, available=False)

    inner = unwrap_sumup_data(payload) if isinstance(payload, dict) else {}
    battery = inner.get("battery_level")
    battery_level = float(battery) if isinstance(battery, (int, float)) else None
    return SumupReaderTelemetryResponse(
        id=reader.id,
        sumup_reader_id=reader.sumup_reader_id,
        label=reader.label,
        device_identifier=reader.device_identifier,
        device_model=reader.device_model,
        telemetry_available=True,
        online_status=_clip(str(inner["status"]), 32) if inner.get("status") else None,
        battery_level=battery_level,
        connection_type=_clip(str(inner["connection_type"]), 32) if inner.get("connection_type") else None,
        firmware_version=_clip(str(inner["firmware_version"]), 64) if inner.get("firmware_version") else None,
        last_activity=_clip(str(inner["last_activity"]), 64) if inner.get("last_activity") else None,
        state=_clip(str(inner["state"]), 64) if inner.get("state") else None,
    )


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
