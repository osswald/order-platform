"""Rental packing / return checklist PDF."""

from __future__ import annotations

from datetime import date

from babel.dates import format_date as babel_format_date

from ...currency import organisation_country_code
from ...i18n import t
from ...models import HireCompany, Rental
from ...rental_service import FLEET_TYPE_ORDER, rental_display_name
from ..base import VqPdf
from ..formatting import hire_company_issuer_lines, resolve_format_locale
from ..logo import resolve_logo_for_hire_company
from ..settings import PdfReportSettings
from ..tables import TableColumn, TableSpec, write_table_header, write_table_row

CHECKBOX = "\u2610"


def _appliance_type_label(typ: str, locale: str) -> str:
    translated = t(f"appliance_type.{typ}", locale)
    # Missing keys fall back to the key path from i18n.t — use raw type then.
    if translated.startswith("appliance_type."):
        return typ or "—"
    return translated


def _device_label(appliance, *, locale: str) -> str:
    name = (getattr(appliance, "name", None) or "").strip() or "—"
    typ = getattr(appliance, "type", None) or ""
    type_label = _appliance_type_label(typ, locale) if typ else ""
    if typ == "printer":
        ip = (getattr(appliance, "ip_address", None) or "").strip() or "—"
        if type_label:
            return f"{name} ({type_label}, {ip})"
        return f"{name} ({ip})"
    if type_label:
        return f"{name} ({type_label})"
    return name


def _type_sort_key(typ: str) -> tuple[int, str]:
    try:
        return (FLEET_TYPE_ORDER.index(typ), typ)
    except ValueError:
        return (len(FLEET_TYPE_ORDER), typ)


def _format_calendar_date(value: date, *, locale: str, country_code: str | None) -> str:
    fmt_locale = resolve_format_locale(locale, country_code)
    return babel_format_date(value, format="medium", locale=fmt_locale)


def _date_range_text(start: date, end: date, *, locale: str, country_code: str | None) -> str:
    start_text = _format_calendar_date(start, locale=locale, country_code=country_code)
    end_text = _format_calendar_date(end, locale=locale, country_code=country_code)
    return f"{start_text} – {end_text}"


def _checklist_table_spec(pdf: VqPdf, locale: str, *, with_quantity: bool) -> TableSpec:
    usable = pdf.content_width
    checkbox_w = usable * 0.08
    if with_quantity:
        return TableSpec(
            columns=(
                TableColumn("", checkbox_w, "C"),
                TableColumn(t("pdf.rental_packing.item", locale), usable * 0.62, "L"),
                TableColumn(t("pdf.rental_packing.qty", locale), usable * 0.30, "R"),
            )
        )
    return TableSpec(
        columns=(
            TableColumn("", checkbox_w, "C"),
            TableColumn(t("pdf.rental_packing.item", locale), usable * 0.92, "L"),
        )
    )


def build_rental_packing_pdf(
    *,
    rental: Rental,
    hire_company: HireCompany,
    settings: PdfReportSettings,
) -> bytes:
    locale = settings.locale
    org = rental.organisation
    country_code = organisation_country_code(org) if org is not None else None

    pdf = VqPdf(locale=locale, title=t("pdf.rental_packing.title", locale))
    _mime, logo_bytes = resolve_logo_for_hire_company(hire_company)
    pdf.write_logo_header_block(logo_bytes, hire_company_issuer_lines(hire_company))

    pdf.write_heading(t("pdf.rental_packing.title", locale))
    pdf.write_text(t("pdf.rental_packing.rental", locale, name=rental_display_name(rental)))
    if org is not None:
        pdf.write_text(t("pdf.rental_packing.organisation", locale, name=org.name))
    pdf.write_text(
        t(
            "pdf.rental_packing.dates",
            locale,
            range=_date_range_text(rental.start_date, rental.end_date, locale=locale, country_code=country_code),
        )
    )
    pdf.write_spacer()

    open_lendings = [
        row for row in (rental.lendings or []) if row.returned_at is None and row.appliance is not None
    ]
    pdf.write_text(t("pdf.rental_packing.devices_heading", locale), size=11)
    device_spec = _checklist_table_spec(pdf, locale, with_quantity=False)
    write_table_header(pdf, device_spec)
    if open_lendings:
        for row in sorted(
            open_lendings,
            key=lambda lending: (
                *_type_sort_key(lending.appliance.type or ""),
                _device_label(lending.appliance, locale=locale),
                lending.id,
            ),
        ):
            write_table_row(pdf, device_spec, [CHECKBOX, _device_label(row.appliance, locale=locale)])
    else:
        pdf.write_muted(t("pdf.rental_packing.no_devices", locale))

    pdf.write_spacer()
    lines = sorted(rental.zubehoer_lines or [], key=lambda row: (row.sort_order, row.id))
    pdf.write_text(t("pdf.rental_packing.zubehoer_heading", locale), size=11)
    with_qty = any(row.quantity is not None for row in lines)
    zubehoer_spec = _checklist_table_spec(pdf, locale, with_quantity=with_qty)
    write_table_header(pdf, zubehoer_spec)
    if lines:
        for row in lines:
            if with_qty:
                qty_text = str(row.quantity) if row.quantity is not None else ""
                write_table_row(pdf, zubehoer_spec, [CHECKBOX, row.label, qty_text])
            else:
                write_table_row(pdf, zubehoer_spec, [CHECKBOX, row.label])
    else:
        pdf.write_muted(t("pdf.rental_packing.no_zubehoer", locale))

    return pdf.output_bytes()
