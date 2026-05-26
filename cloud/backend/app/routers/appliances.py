import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..appliance_naming import generate_appliance_name
from ..models import Appliance, ApplianceLending, Organisation
from ..security import get_password_hash
from ..deps import get_db
from ..tenancy import TenantContext, ensure_org_in_tenant, get_current_tenant_admin

router = APIRouter()

ALLOWED_TYPES = {"server", "printer", "mobile", "tablet", "router", "ap"}
IPV4_PATTERN = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

AUTO_NAMED_TYPES = {"server", "printer"}


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _intervals_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """Inclusive interval overlap; used for documentation / tests — SQL uses equivalent column compares."""
    return a_start <= b_end and b_start <= a_end


def _assert_lending_is_planned(lending: ApplianceLending, today: date) -> None:
    if lending.returned_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lending already returned",
        )
    if lending.start_date <= today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only planned lendings can be cancelled",
        )


def _lending_segment(l: ApplianceLending, today: date) -> str:
    """past | current | future — see plan: future = start > today and not returned; past = end < today or returned."""
    if l.returned_at is not None:
        return "past"
    if l.start_date > today:
        return "future"
    if l.end_date < today:
        return "past"
    if l.start_date <= today <= l.end_date:
        return "current"
    return "past"


class ApplianceBase(BaseModel):
    type: str = Field(..., description="Device type")
    name: str | None = None
    ip_address: str | None = None
    model: str | None = Field(None, max_length=255)
    comment: str | None = Field(None, max_length=2000)


class ApplianceCreate(ApplianceBase):
    @model_validator(mode="after")
    def validate_printer_ip(self):
        self.ip_address = _validate_ip_for_type(self.ip_address, self.type)
        return self


class ApplianceUpdate(BaseModel):
    type: str | None = Field(None, description="Device type")
    name: str | None = Field(None, max_length=255)
    ip_address: str | None = None
    model: str | None = Field(None, max_length=255)
    comment: str | None = Field(None, max_length=2000)


class CurrentLendingRead(BaseModel):
    organisation_id: int
    organisation_name: str
    start_date: date
    end_date: date


class ApplianceLendingRead(BaseModel):
    id: int
    organisation_id: int
    organisation_name: str
    start_date: date
    end_date: date
    returned_at: datetime | None
    segment: str


class ApplianceRead(ApplianceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lending_status: str = "available"
    current_lending: CurrentLendingRead | None = None
    lendings: list[ApplianceLendingRead] | None = None
    lendable: bool = True
    lend_block_reason: str | None = None
    edge_client_id: str | None = None


class ApplianceAdminCreated(ApplianceRead):
    """Admin-only response when edge credentials are issued."""

    edge_secret: str | None = Field(None, description="Plain secret; returned only when created or rotated")


class AppliancePairingSessionRead(BaseModel):
    id: int
    appliance_id: int
    pairing_code: str
    pairing_code_display: str
    expires_at: datetime
    setup_url: str = "http://192.168.192.10"


class ApplianceLendingCreate(BaseModel):
    organisation_id: int
    start_date: date
    duration_days: int = Field(..., ge=1)


def _appliance_to_read(
    appliance: Appliance,
    *,
    today: date,
    active_by_appliance_id: dict[int, ApplianceLending] | None = None,
    include_lendings: bool = False,
    lendable: bool = True,
    lend_block_reason: str | None = None,
) -> ApplianceRead:
    current_row: ApplianceLending | None = None
    if active_by_appliance_id is not None:
        current_row = active_by_appliance_id.get(appliance.id)
    else:
        for lending in getattr(appliance, "lendings", []) or []:
            if (
                lending.returned_at is None
                and lending.start_date <= today <= lending.end_date
            ):
                current_row = lending
                break

    current_lending: CurrentLendingRead | None = None
    lending_status = "available"
    if current_row is not None:
        lending_status = "lent"
        org_name = current_row.organisation.name if current_row.organisation else ""
        current_lending = CurrentLendingRead(
            organisation_id=current_row.organisation_id,
            organisation_name=org_name,
            start_date=current_row.start_date,
            end_date=current_row.end_date,
        )

    lendings_list: list[ApplianceLendingRead] | None = None
    if include_lendings:
        rows = sorted(
            getattr(appliance, "lendings", []) or [],
            key=lambda x: (x.start_date, x.id),
            reverse=True,
        )
        lendings_list = []
        for row in rows:
            org_name = row.organisation.name if row.organisation else ""
            lendings_list.append(
                ApplianceLendingRead(
                    id=row.id,
                    organisation_id=row.organisation_id,
                    organisation_name=org_name,
                    start_date=row.start_date,
                    end_date=row.end_date,
                    returned_at=row.returned_at,
                    segment=_lending_segment(row, today),
                )
            )

    return ApplianceRead(
        id=appliance.id,
        type=appliance.type,
        name=appliance.name,
        ip_address=appliance.ip_address,
        model=appliance.model,
        comment=appliance.comment,
        lending_status=lending_status,
        current_lending=current_lending,
        lendings=lendings_list,
        lendable=lendable,
        lend_block_reason=lend_block_reason,
        edge_client_id=getattr(appliance, "edge_client_id", None),
    )


def _validate_ip_for_type(ip: str | None, appliance_type: str | None) -> str | None:
    if ip is None or ip == "":
        return None
    ip = ip.strip()
    if appliance_type and appliance_type.lower() != "printer":
        raise ValueError("IP address is only allowed for printers")
    if not IPV4_PATTERN.match(ip):
        raise ValueError("Invalid IPv4 address")
    return ip


def validate_type(value: str) -> str:
    lower_value = value.lower()
    if lower_value not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Appliance type must be one of: {', '.join(sorted(ALLOWED_TYPES))}",
        )
    return lower_value


def _apply_auto_name(
    db: Session,
    appliance: Appliance,
    *,
    force: bool = False,
) -> None:
    if appliance.type not in AUTO_NAMED_TYPES:
        return
    if appliance.name and not force:
        return
    appliance.name = generate_appliance_name(db, appliance.type, exclude_id=appliance.id)


def _clear_printer_only_fields(appliance: Appliance) -> None:
    if appliance.type != "printer":
        appliance.ip_address = None


def _get_appliance_in_tenant(db: Session, appliance_id: int, hire_company_id: int) -> Appliance:
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if not appliance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appliance not found")
    if appliance.hire_company_id != hire_company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Appliance not in this Verleiher")
    return appliance


def _generate_pairing_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _format_pairing_code(code: str) -> str:
    return f"{code[:3]}-{code[3:]}"


@router.get("/", response_model=List[ApplianceRead])
def read_appliances(
    lend_check_start: date | None = Query(None),
    lend_check_duration: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    today = _utc_today()
    appliances = (
        db.query(Appliance)
        .filter(Appliance.hire_company_id == tenant.hire_company_id)
        .order_by(Appliance.id)
        .all()
    )
    if not appliances:
        return []

    appliance_ids = [a.id for a in appliances]
    active_rows = (
        db.query(ApplianceLending)
        .options(joinedload(ApplianceLending.organisation))
        .filter(
            ApplianceLending.appliance_id.in_(appliance_ids),
            ApplianceLending.returned_at.is_(None),
            ApplianceLending.start_date <= today,
            ApplianceLending.end_date >= today,
        )
        .all()
    )
    active_by_id = {row.appliance_id: row for row in active_rows}

    blocked_by_id: dict[int, str] = {}
    if lend_check_start is not None and lend_check_duration is not None:
        check_end = lend_check_start + timedelta(days=lend_check_duration - 1)
        overlap_rows = (
            db.query(ApplianceLending)
            .options(joinedload(ApplianceLending.organisation))
            .filter(
                ApplianceLending.appliance_id.in_(appliance_ids),
                ApplianceLending.returned_at.is_(None),
                ApplianceLending.start_date <= check_end,
                ApplianceLending.end_date >= lend_check_start,
            )
            .all()
        )
        for row in overlap_rows:
            org_name = row.organisation.name if row.organisation else ""
            blocked_by_id[row.appliance_id] = (
                f"Überschneidung mit offener Ausleihe{f' ({org_name})' if org_name else ''}"
            )

    return [
        _appliance_to_read(
            a,
            today=today,
            active_by_appliance_id=active_by_id,
            include_lendings=False,
            lendable=a.id not in blocked_by_id,
            lend_block_reason=blocked_by_id.get(a.id),
        )
        for a in appliances
    ]


@router.get("/{appliance_id}", response_model=ApplianceRead)
def read_appliance(
    appliance_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    today = _utc_today()
    _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
    appliance = (
        db.query(Appliance)
        .options(
            joinedload(Appliance.lendings).joinedload(ApplianceLending.organisation),
        )
        .filter(Appliance.id == appliance_id)
        .first()
    )
    return _appliance_to_read(appliance, today=today, active_by_appliance_id=None, include_lendings=True)


@router.post("/", response_model=ApplianceAdminCreated)
def create_appliance(
    appliance_in: ApplianceCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    appliance_type = validate_type(appliance_in.type)

    appliance = Appliance(
        hire_company_id=tenant.hire_company_id,
        type=appliance_type,
        model=appliance_in.model,
        comment=appliance_in.comment,
        ip_address=appliance_in.ip_address if appliance_type == "printer" else None,
    )
    if appliance_type in AUTO_NAMED_TYPES:
        appliance.name = generate_appliance_name(db, appliance_type)
    else:
        appliance.name = (appliance_in.name or "").strip() or None

    edge_secret_out: str | None = None
    if appliance_type == "server":
        appliance.edge_client_id = uuid4().hex
        edge_secret_out = secrets.token_urlsafe(32)
        appliance.edge_secret_hash = get_password_hash(edge_secret_out)

    db.add(appliance)
    db.commit()
    db.refresh(appliance)
    today = _utc_today()
    read = _appliance_to_read(appliance, today=today, active_by_appliance_id={}, include_lendings=False)
    d = read.model_dump() if hasattr(read, "model_dump") else read.dict()
    d["edge_secret"] = edge_secret_out
    return ApplianceAdminCreated(**d)


@router.put("/{appliance_id}", response_model=ApplianceRead)
def update_appliance(
    appliance_id: int,
    appliance_in: ApplianceUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    appliance = _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)

    previous_type = appliance.type
    new_type = validate_type(appliance_in.type) if appliance_in.type is not None else appliance.type

    if appliance_in.type is not None:
        appliance.type = new_type

    if appliance_in.model is not None:
        appliance.model = appliance_in.model or None
    if appliance_in.comment is not None:
        appliance.comment = appliance_in.comment or None

    if new_type == "printer":
        if appliance_in.ip_address is not None:
            appliance.ip_address = _validate_ip_for_type(appliance_in.ip_address, "printer")
    else:
        _clear_printer_only_fields(appliance)

    if new_type in AUTO_NAMED_TYPES:
        if previous_type != new_type or not appliance.name:
            _apply_auto_name(db, appliance, force=True)
        elif appliance_in.name is not None:
            appliance.name = appliance_in.name.strip() or appliance.name
    elif appliance_in.name is not None:
        appliance.name = appliance_in.name.strip() or None

    db.commit()
    db.refresh(appliance)
    today = _utc_today()
    active_rows = (
        db.query(ApplianceLending)
        .options(joinedload(ApplianceLending.organisation))
        .filter(
            ApplianceLending.appliance_id == appliance.id,
            ApplianceLending.returned_at.is_(None),
            ApplianceLending.start_date <= today,
            ApplianceLending.end_date >= today,
        )
        .all()
    )
    active_by_id = {row.appliance_id: row for row in active_rows}
    return _appliance_to_read(appliance, today=today, active_by_appliance_id=active_by_id, include_lendings=False)


@router.post(
    "/{appliance_id}/edge-credentials",
    response_model=ApplianceAdminCreated,
)
def rotate_appliance_edge_credentials(
    appliance_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    appliance = _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
    if appliance.type != "server":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Edge credentials are only for server appliances",
        )
    appliance.edge_client_id = uuid4().hex
    secret = secrets.token_urlsafe(32)
    appliance.edge_secret_hash = get_password_hash(secret)
    db.commit()
    db.refresh(appliance)
    today = _utc_today()
    read = _appliance_to_read(appliance, today=today, active_by_appliance_id={}, include_lendings=False)
    d = read.model_dump() if hasattr(read, "model_dump") else read.dict()
    d["edge_secret"] = secret
    return ApplianceAdminCreated(**d)


@router.delete(
    "/{appliance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_appliance(
    appliance_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    appliance = _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
    db.delete(appliance)
    db.commit()
    return None


@router.post(
    "/{appliance_id}/lendings",
    response_model=ApplianceRead,
)
def create_appliance_lending(
    appliance_id: int,
    body: ApplianceLendingCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
    ensure_org_in_tenant(db, body.organisation_id, tenant.hire_company_id)

    # Inclusive end: duration_days calendar days including start_date.
    end_date = body.start_date + timedelta(days=body.duration_days - 1)

    open_overlap = (
        db.query(ApplianceLending)
        .filter(
            ApplianceLending.appliance_id == appliance_id,
            ApplianceLending.returned_at.is_(None),
            ApplianceLending.start_date <= end_date,
            ApplianceLending.end_date >= body.start_date,
        )
        .first()
    )
    if open_overlap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appliance already has an open lending overlapping this period",
        )

    lending = ApplianceLending(
        appliance_id=appliance_id,
        organisation_id=body.organisation_id,
        start_date=body.start_date,
        end_date=end_date,
        returned_at=None,
    )
    db.add(lending)
    db.commit()

    today = _utc_today()
    appliance = (
        db.query(Appliance)
        .options(
            joinedload(Appliance.lendings).joinedload(ApplianceLending.organisation),
        )
        .filter(Appliance.id == appliance_id)
        .first()
    )
    return _appliance_to_read(appliance, today=today, active_by_appliance_id=None, include_lendings=True)


@router.post(
    "/{appliance_id}/lendings/{lending_id}/return",
    response_model=ApplianceRead,
)
def return_appliance_lending(
    appliance_id: int,
    lending_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
    lending = (
        db.query(ApplianceLending)
        .filter(
            ApplianceLending.id == lending_id,
            ApplianceLending.appliance_id == appliance_id,
        )
        .first()
    )
    if not lending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lending not found")
    # 400 if already returned (not idempotent) — documented choice.
    if lending.returned_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lending already returned",
        )

    lending.returned_at = datetime.now(timezone.utc)
    db.commit()

    today = _utc_today()
    appliance = (
        db.query(Appliance)
        .options(
            joinedload(Appliance.lendings).joinedload(ApplianceLending.organisation),
        )
        .filter(Appliance.id == appliance_id)
        .first()
    )
    return _appliance_to_read(appliance, today=today, active_by_appliance_id=None, include_lendings=True)


@router.delete(
    "/{appliance_id}/lendings/{lending_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_planned_appliance_lending(
    appliance_id: int,
    lending_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    _get_appliance_in_tenant(db, appliance_id, tenant.hire_company_id)
    lending = (
        db.query(ApplianceLending)
        .filter(
            ApplianceLending.id == lending_id,
            ApplianceLending.appliance_id == appliance_id,
        )
        .first()
    )
    if not lending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lending not found")

    _assert_lending_is_planned(lending, _utc_today())
    db.delete(lending)
    db.commit()
    return None
