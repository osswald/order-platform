"""Tests for reusable PDF framework."""

import base64
from io import BytesIO

import pytest
from app.locale_format import format_money
from app.models import Event, HireCompany, Organisation
from app.pdf.assets import VENDIQO_LOGO, asset_bytes
from app.pdf.base import VqPdf
from app.pdf.formatting import organisation_issuer_lines, safe_filename
from app.pdf.logo import resolve_logo_for_event
from app.pdf.response import pdf_download_response
from app.pdf.tables import TableColumn, TableSpec, write_table_header, write_table_row
from app.receipt_printing_config import store_receipt_logo
from pypdf import PdfReader


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _pdf_pages(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(BytesIO(pdf_bytes))
    return [page.extract_text() or "" for page in reader.pages]


def test_write_table_row_does_not_duplicate_text():
    pdf = VqPdf(locale="de", title="Table test")
    spec = TableSpec(
        columns=(
            TableColumn("Artikel", 100, "L"),
            TableColumn("Menge", 30, "R"),
        )
    )
    write_table_header(pdf, spec)
    write_table_row(pdf, spec, ["EinzigartigerArtikel", "2"])
    text = _pdf_text(pdf.output_bytes())
    assert text.count("EinzigartigerArtikel") == 1
    assert text.count("2") >= 1


def test_table_row_columns_not_split_across_pages():
    pdf = VqPdf(locale="de", title="Break test")
    spec = TableSpec(
        columns=(
            TableColumn("Artikel", 80, "L"),
            TableColumn("Menge", 25, "R"),
            TableColumn("Betrag", 35, "R"),
        )
    )
    pdf.write_text("\n".join(["Füller"] * 45))
    write_table_header(pdf, spec)
    write_table_row(pdf, spec, ["Mineral mit 0.5l", "2", "10.00 CHF"])
    orphan_headers = {"Artikel", "Menge", "Einzelpreis", "Betrag"}
    for page_text in _pdf_pages(pdf.output_bytes()):
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        for line in lines:
            assert line not in orphan_headers
        if "Mineral mit 0.5l" in page_text:
            assert "10.00 CHF" in page_text


def test_content_bottom_reserves_footer_space():
    pdf = VqPdf(locale="de", title="Footer reserve")
    assert pdf.content_bottom == pdf.h - pdf.BODY_BOTTOM_MARGIN_MM - pdf.FOOTER_HEIGHT_MM


def test_vqpdf_renders_unicode_pdf():
    pdf = VqPdf(locale="de", title="Test")
    pdf.write_text("Grüsse aus Zürich — Umlaut test")
    raw = pdf.output_bytes()
    assert raw.startswith(b"%PDF")
    assert len(raw) > 500


def test_write_logo_header_block_smoke():
    pdf = VqPdf(locale="de")
    logo = asset_bytes(VENDIQO_LOGO)
    pdf.write_logo_header_block(logo, ["Test Organisation", "Bahnhofstrasse 1", "8001 Zürich"])
    pdf.write_text("Body")
    raw = pdf.output_bytes()
    assert raw.startswith(b"%PDF")
    assert len(raw) > 1000


def test_format_money_locale():
    assert format_money(1250, locale="de", currency="CHF") == "CHF 12.50"
    assert format_money(1250, locale="en", currency="CHF") == "CHF 12.50"
    assert format_money(1250, locale="de", currency="CHF").startswith("CHF ")


def test_safe_filename():
    assert safe_filename("Team A / Bar") == "Team-A-Bar"
    assert safe_filename("   ") == "document"


def test_pdf_download_response_headers():
    response = pdf_download_response(b"%PDF-1.4", "Sammelrechnung-Team.pdf")
    assert response.media_type == "application/pdf"
    assert "Sammelrechnung-Team.pdf" in response.headers["content-disposition"]


def test_organisation_issuer_lines():
    org = Organisation(name="Org", address="Street 1", zip="8000", city="Zürich", country_id=1, hire_company_id=1)
    lines = organisation_issuer_lines(org)
    assert lines[0] == "Org"
    assert "8000" in lines[-1]


@pytest.mark.parametrize(
    ("which", "expected_prefix"),
    [
        ("event", b"\x89PNG"),
        ("org", b"\x89PNG"),
        ("hire", b"\x89PNG"),
        ("none", b"\x89PNG"),
    ],
)
def test_resolve_logo_for_event_cascade(which, expected_prefix):
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    hire = HireCompany(name="HC")
    org = Organisation(name="Org", country_id=1, hire_company_id=1, hire_company=hire)
    event = Event(
        name="Fest",
        status="active",
        start="2026-01-01T00:00:00+00:00",
        end="2026-01-02T00:00:00+00:00",
        organisation_id=1,
        organisation=org,
    )
    if which in ("event", "org", "hire"):
        target = {"event": event, "org": org, "hire": hire}[which]
        store_receipt_logo(target, "image/png", png)
    mime, data = resolve_logo_for_event(event)
    assert mime.startswith("image/")
    assert data[:4] == expected_prefix[:4] or data[:4] == b"\x89PNG"
