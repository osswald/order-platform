"""Shared PDF report settings for cloud document generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfReportSettings:
    """Base options passed to PDF document builders."""

    locale: str = "de"


@dataclass(frozen=True)
class CollectiveBillPdfSettings(PdfReportSettings):
    """Options for Sammelrechnung PDF documents."""

    include_order_detail: bool = False
