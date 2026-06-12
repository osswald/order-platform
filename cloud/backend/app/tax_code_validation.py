"""Validation helpers for organisation and article tax code assignments."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from .i18n.errors import api_error
from .models import Organisation, TaxCode


def get_tax_code_or_404(db: Session, tax_code_id: int) -> TaxCode:
    tax_code = db.query(TaxCode).filter(TaxCode.id == tax_code_id).first()
    if not tax_code:
        raise api_error("tax_code_not_found", status.HTTP_404_NOT_FOUND)
    return tax_code


def ensure_tax_code_for_country(db: Session, tax_code_id: int, country_id: int) -> TaxCode:
    tax_code = get_tax_code_or_404(db, tax_code_id)
    if tax_code.country_id != country_id:
        raise api_error("invalid_tax_code_for_country", status.HTTP_400_BAD_REQUEST)
    return tax_code


def apply_organisation_vat_settings(
    db: Session,
    org: Organisation,
    *,
    vat_liable: bool | None = None,
    default_tax_code_id: int | None = None,
    vat_liable_set: bool = False,
    default_tax_code_id_set: bool = False,
) -> None:
    if vat_liable_set:
        org.vat_liable = bool(vat_liable)
    if default_tax_code_id_set:
        org.default_tax_code_id = default_tax_code_id

    if org.vat_liable:
        if org.default_tax_code_id is None:
            raise api_error("default_tax_code_required", status.HTTP_400_BAD_REQUEST)
        ensure_tax_code_for_country(db, org.default_tax_code_id, org.country_id)
    else:
        org.default_tax_code_id = None


def validate_article_tax_code(
    db: Session,
    organisation: Organisation,
    tax_code_id: int | None,
) -> None:
    if organisation.vat_liable:
        if tax_code_id is None:
            raise api_error("article_tax_code_required", status.HTTP_400_BAD_REQUEST)
        ensure_tax_code_for_country(db, tax_code_id, organisation.country_id)
        return
    if tax_code_id is not None:
        raise api_error("article_tax_code_not_allowed", status.HTTP_400_BAD_REQUEST)
