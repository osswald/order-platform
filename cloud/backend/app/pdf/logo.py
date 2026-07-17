"""Runtime logo resolution for PDF documents."""

from __future__ import annotations

from ..receipt_printing_config import has_receipt_logo, receipt_logo_bytes
from .assets import VENDIQO_LOGO, asset_bytes


def resolve_logo_for_event(event) -> tuple[str, bytes]:
    """Cascade: event → organisation → hire_company → bundled Vendiqo logo."""
    organisation = getattr(event, "organisation", None)
    hire_company = getattr(organisation, "hire_company", None) if organisation else None
    for entity in (event, organisation, hire_company):
        if entity is not None and has_receipt_logo(entity):
            result = receipt_logo_bytes(entity)
            if result is not None:
                return result
    return "image/png", asset_bytes(VENDIQO_LOGO)
