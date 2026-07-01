from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..appliance_naming import appliance_display_name
from ..auth_deps import get_current_user
from ..dashboard_summary import build_organisation_dashboard_summary
from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import ApplianceLending, Event, HireCompany, Organisation, User, UserOrganisationOnboardingDismissal
from ..onboarding_tasks import complete_onboarding_task, dismiss_onboarding_task
from ..reference_countries import country_response, get_country_or_404
from ..schemas.dashboard import DashboardSummaryRead
from ..tax_code_validation import apply_organisation_vat_settings, ensure_tax_code_for_country
from ..tenancy import (
    TenantContext,
    ensure_can_manage_organisation,
    ensure_org_in_tenant,
    ensure_user_can_use_organisation,
    ensure_users_in_tenant,
    get_current_organisation_manager,
    get_current_tenant,
    get_current_tenant_admin,
    readable_events_query,
    readable_organisations,
)
from .appliances import _assert_lending_is_planned, _utc_today

router = APIRouter()


class CountryRead(BaseModel):
    id: int
    code: str
    name: str


class OrganisationBase(BaseModel):
    name: str = Field(..., min_length=1)
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country_id: int
    currency: str = Field(..., min_length=3, max_length=3)

    @model_validator(mode="after")
    def normalize_currency(self):
        self.currency = self.currency.upper()
        return self


class OrganisationCreate(OrganisationBase):
    user_ids: list[int] | None = None


class OrganisationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    country_id: int | None = None
    currency: str | None = Field(None, min_length=3, max_length=3)
    user_ids: list[int] | None = None
    vat_liable: bool | None = None
    default_tax_code_id: int | None = None
    accounts_enabled: bool | None = None
    position_comments_enabled: bool | None = None


class TaxCodeSummaryRead(BaseModel):
    id: int
    name: str


class OrganisationRead(OrganisationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hire_company_id: int
    country: CountryRead
    user_ids: list[int] = []
    vat_liable: bool = False
    default_tax_code_id: int | None = None
    default_tax_code: TaxCodeSummaryRead | None = None
    accounts_enabled: bool = False
    position_comments_enabled: bool = False


class OrgApplianceLendingItem(BaseModel):
    lending_id: int
    appliance_id: int
    appliance_name: str | None
    appliance_type: str
    start_date: date
    end_date: date


class OrganisationApplianceLendingsRead(BaseModel):
    current: list[OrgApplianceLendingItem]
    planned: list[OrgApplianceLendingItem]
    past: list[OrgApplianceLendingItem]


def organisation_response(org: Organisation) -> dict:
    default_tax_code = None
    if org.default_tax_code_id is not None and org.default_tax_code is not None:
        default_tax_code = {"id": org.default_tax_code.id, "name": org.default_tax_code.name}
    return {
        "id": org.id,
        "hire_company_id": org.hire_company_id,
        "name": org.name,
        "address": org.address,
        "zip": org.zip,
        "city": org.city,
        "country_id": org.country_id,
        "country": country_response(org.country),
        "currency": org.currency,
        "user_ids": [user.id for user in org.users],
        "vat_liable": bool(org.vat_liable),
        "default_tax_code_id": org.default_tax_code_id,
        "default_tax_code": default_tax_code,
        "accounts_enabled": bool(org.accounts_enabled),
        "position_comments_enabled": bool(org.position_comments_enabled),
    }


@router.get("/", response_model=list[OrganisationRead])
def read_organisations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_organisation_manager),
):
    organisations = readable_organisations(db, current_user, tenant.hire_company_id)
    return [organisation_response(org) for org in organisations]


@router.get(
    "/{organisation_id}/appliance-lendings",
    response_model=OrganisationApplianceLendingsRead,
)
def read_organisation_appliance_lendings(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)

    today = datetime.now(UTC).date()
    rows = (
        db.query(ApplianceLending)
        .options(joinedload(ApplianceLending.appliance))
        .filter(ApplianceLending.organisation_id == organisation_id)
        .order_by(ApplianceLending.start_date.desc(), ApplianceLending.id.desc())
        .all()
    )

    current: list[OrgApplianceLendingItem] = []
    planned: list[OrgApplianceLendingItem] = []
    past: list[OrgApplianceLendingItem] = []

    for row in rows:
        appliance = row.appliance
        if appliance and appliance.hire_company_id != tenant.hire_company_id:
            continue
        item = OrgApplianceLendingItem(
            lending_id=row.id,
            appliance_id=row.appliance_id,
            appliance_name=appliance_display_name(appliance),
            appliance_type=appliance.type if appliance else "",
            start_date=row.start_date,
            end_date=row.end_date,
        )
        if row.returned_at is not None:
            past.append(item)
            continue
        if row.end_date < today:
            past.append(item)
            continue
        if row.start_date > today:
            planned.append(item)
            continue
        if row.start_date <= today <= row.end_date:
            current.append(item)
        else:
            past.append(item)

    return OrganisationApplianceLendingsRead(current=current, planned=planned, past=past)


@router.get("/{organisation_id}/dashboard-summary", response_model=DashboardSummaryRead)
def read_organisation_dashboard_summary(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    organisation = ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    events = (
        readable_events_query(db, current_user, tenant.hire_company_id)
        .filter(Event.organisation_id == organisation_id)
        .order_by(Event.start.desc())
        .all()
    )
    return build_organisation_dashboard_summary(db, organisation, events, user_id=current_user.id)


@router.post(
    "/{organisation_id}/onboarding/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
)
def dismiss_organisation_onboarding(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    existing = (
        db.query(UserOrganisationOnboardingDismissal)
        .filter(
            UserOrganisationOnboardingDismissal.user_id == current_user.id,
            UserOrganisationOnboardingDismissal.organisation_id == organisation_id,
        )
        .first()
    )
    if existing is None:
        db.add(
            UserOrganisationOnboardingDismissal(
                user_id=current_user.id,
                organisation_id=organisation_id,
            )
        )
        commit_or_raise(db)
    return None


@router.post(
    "/{organisation_id}/onboarding/tasks/{task_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
)
def complete_organisation_onboarding_task(
    organisation_id: int,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    complete_onboarding_task(
        db,
        user_id=current_user.id,
        organisation_id=organisation_id,
        task_id=task_id,
    )
    commit_or_raise(db)
    return None


@router.post(
    "/{organisation_id}/onboarding/tasks/{task_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
)
def dismiss_organisation_onboarding_task(
    organisation_id: int,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    dismiss_onboarding_task(
        db,
        user_id=current_user.id,
        organisation_id=organisation_id,
        task_id=task_id,
    )
    commit_or_raise(db)
    return None


@router.delete(
    "/{organisation_id}/appliance-lendings/{lending_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_organisation_planned_lending(
    organisation_id: int,
    lending_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)

    lending = (
        db.query(ApplianceLending)
        .options(joinedload(ApplianceLending.appliance))
        .filter(
            ApplianceLending.id == lending_id,
            ApplianceLending.organisation_id == organisation_id,
        )
        .first()
    )
    if not lending:
        raise api_error("lending_not_found", status.HTTP_404_NOT_FOUND)
    if lending.appliance and lending.appliance.hire_company_id != tenant.hire_company_id:
        raise api_error("lending_not_in_verleiher", status.HTTP_403_FORBIDDEN)

    _assert_lending_is_planned(lending, _utc_today())
    db.delete(lending)
    commit_or_raise(db)
    return None


@router.get("/{organisation_id}", response_model=OrganisationRead)
def read_organisation(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_organisation_manager),
):
    org = ensure_user_can_use_organisation(db, current_user, organisation_id, tenant.hire_company_id)
    return organisation_response(org)


@router.post("/", response_model=OrganisationRead, status_code=status.HTTP_201_CREATED)
def create_organisation(
    org_in: OrganisationCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    get_country_or_404(db, org_in.country_id)
    db_org = Organisation(
        hire_company_id=tenant.hire_company_id,
        name=org_in.name,
        address=org_in.address,
        zip=org_in.zip,
        city=org_in.city,
        country_id=org_in.country_id,
        currency=org_in.currency,
    )
    if org_in.user_ids:
        db_org.users = ensure_users_in_tenant(db, org_in.user_ids, tenant.hire_company_id)
    db.add(db_org)
    db.flush()
    hire_company = db.query(HireCompany).filter(HireCompany.id == tenant.hire_company_id).first()
    if hire_company:
        from ..receipt_printing_config import copy_receipt_printing_from_hire_company

        copy_receipt_printing_from_hire_company(hire_company, db_org)
    commit_or_raise(db)
    db_org = ensure_org_in_tenant(db, db_org.id, tenant.hire_company_id)
    return organisation_response(db_org)


@router.put("/{organisation_id}", response_model=OrganisationRead)
def update_organisation(
    organisation_id: int,
    org_in: OrganisationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
):
    ensure_can_manage_organisation(current_user, organisation_id)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    if org_in.name is not None:
        org.name = org_in.name
    if org_in.address is not None:
        org.address = org_in.address
    if org_in.zip is not None:
        org.zip = org_in.zip
    if org_in.city is not None:
        org.city = org_in.city
    if org_in.country_id is not None:
        get_country_or_404(db, org_in.country_id)
        new_country_id = org_in.country_id
        if (
            new_country_id != org.country_id
            and org.default_tax_code_id is not None
            and org.vat_liable
        ):
            ensure_tax_code_for_country(db, org.default_tax_code_id, new_country_id)
        org.country_id = new_country_id
    if org_in.currency is not None:
        org.currency = org_in.currency.upper()
    if org_in.user_ids is not None:
        org.users = ensure_users_in_tenant(db, org_in.user_ids, tenant.hire_company_id)

    update_fields = org_in.model_dump(exclude_unset=True)
    apply_organisation_vat_settings(
        db,
        org,
        vat_liable=org_in.vat_liable,
        default_tax_code_id=org_in.default_tax_code_id,
        vat_liable_set="vat_liable" in update_fields,
        default_tax_code_id_set="default_tax_code_id" in update_fields,
    )
    if "accounts_enabled" in update_fields:
        org.accounts_enabled = bool(org_in.accounts_enabled)
    if "position_comments_enabled" in update_fields:
        org.position_comments_enabled = bool(org_in.position_comments_enabled)
    commit_or_raise(db)
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    return organisation_response(org)


@router.delete("/{organisation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organisation(
    organisation_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant_admin),
):
    org = ensure_org_in_tenant(db, organisation_id, tenant.hire_company_id)
    db.delete(org)
    commit_or_raise(db)
    return {"detail": "Organisation deleted"}
