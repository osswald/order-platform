"""Reusable table layout for PDF documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .base import VqPdf

Align = Literal["L", "C", "R"]

HEADER_ROW_HEIGHT_MM = 6.0
ROW_PADDING_MM = 0.8


@dataclass(frozen=True)
class TableColumn:
    header: str
    width_mm: float
    align: Align = "L"


@dataclass(frozen=True)
class TableSpec:
    columns: tuple[TableColumn, ...]

    @property
    def total_width_mm(self) -> float:
        return sum(col.width_mm for col in self.columns)


def _page_bottom(pdf: VqPdf) -> float:
    return pdf.content_bottom


def _line_count(pdf: VqPdf, width_mm: float, text: str, row_height: float, align: Align) -> int:
    lines = pdf.multi_cell(
        width_mm,
        row_height,
        text,
        border=0,
        align=align,
        dry_run=True,
        output="LINES",
    )
    return max(1, len(lines))


def _measure_row_height(
    pdf: VqPdf,
    spec: TableSpec,
    row_values: list[str],
    *,
    row_height: float,
) -> float:
    inner_pad = ROW_PADDING_MM * 2
    max_h = row_height
    pdf.set_font(pdf.body_font, size=9)
    for col_idx, col in enumerate(spec.columns):
        text = row_values[col_idx] if col_idx < len(row_values) else ""
        inner_w = max(1.0, col.width_mm - inner_pad)
        line_count = _line_count(pdf, inner_w, text, row_height, col.align)
        max_h = max(max_h, line_count * row_height)
    return max_h


def _ensure_table_space(pdf: VqPdf, spec: TableSpec, needed_mm: float) -> None:
    if pdf.get_y() + needed_mm > _page_bottom(pdf):
        pdf.add_page()
        write_table_header(pdf, spec)


def write_table_header(pdf: VqPdf, spec: TableSpec) -> None:
    if pdf.get_y() + HEADER_ROW_HEIGHT_MM > _page_bottom(pdf):
        pdf.add_page()

    pdf.set_font(pdf.body_font, size=9)
    pdf.set_fill_color(240, 240, 240)
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    auto_pb = pdf.auto_page_break
    pdf.set_auto_page_break(auto=False)
    try:
        for col in spec.columns:
            pdf.set_xy(x0, y0)
            pdf.cell(col.width_mm, HEADER_ROW_HEIGHT_MM, col.header, border=1, align=col.align, fill=True)
            x0 += col.width_mm
    finally:
        pdf.set_auto_page_break(auto_pb, margin=pdf.page_break_margin)

    pdf.set_xy(pdf.l_margin, y0 + HEADER_ROW_HEIGHT_MM)
    pdf.set_fill_color(255, 255, 255)


def _draw_row(
    pdf: VqPdf,
    spec: TableSpec,
    row_values: list[str],
    *,
    row_height: float,
    max_h: float,
) -> None:
    padding = ROW_PADDING_MM
    inner_pad = padding * 2
    x0 = pdf.l_margin
    y0 = pdf.get_y()

    auto_pb = pdf.auto_page_break
    pdf.set_auto_page_break(auto=False)
    try:
        x0 = pdf.l_margin
        for col in spec.columns:
            pdf.rect(x0, y0, col.width_mm, max_h)
            x0 += col.width_mm

        x0 = pdf.l_margin
        pdf.set_font(pdf.body_font, size=9)
        for col_idx, col in enumerate(spec.columns):
            text = row_values[col_idx] if col_idx < len(row_values) else ""
            pdf.set_xy(x0 + padding, y0 + padding)
            inner_w = max(1.0, col.width_mm - inner_pad)
            pdf.multi_cell(inner_w, row_height, text, border=0, align=col.align)
            x0 += col.width_mm
    finally:
        pdf.set_auto_page_break(auto_pb, margin=pdf.page_break_margin)

    pdf.set_xy(pdf.l_margin, y0 + max_h)


def write_table_row(
    pdf: VqPdf,
    spec: TableSpec,
    values: list[str],
    *,
    row_height: float = 5.5,
    continuation_rows: list[list[str]] | None = None,
) -> None:
    rows = [values] + (continuation_rows or [])
    for row_idx, row_values in enumerate(rows):
        max_h = _measure_row_height(pdf, spec, row_values, row_height=row_height)
        _ensure_table_space(pdf, spec, max_h)
        _draw_row(pdf, spec, row_values, row_height=row_height, max_h=max_h)
        if row_idx < len(rows) - 1:
            pdf.set_font(pdf.body_font, size=8)
            pdf.set_text_color(90, 90, 90)
        else:
            pdf.set_text_color(0, 0, 0)


def write_table_total_row(
    pdf: VqPdf,
    spec: TableSpec,
    label: str,
    amount: str,
    *,
    row_height: float = 5.5,
) -> None:
    leading_cols = len(spec.columns) - 1
    label_width = sum(col.width_mm for col in spec.columns[:leading_cols])
    amount_col = spec.columns[-1]
    max_h = row_height
    _ensure_table_space(pdf, spec, max_h)

    x0 = pdf.l_margin
    y0 = pdf.get_y()
    auto_pb = pdf.auto_page_break
    pdf.set_auto_page_break(auto=False)
    try:
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(x0, y0, label_width, max_h, style="FD")
        pdf.rect(x0 + label_width, y0, amount_col.width_mm, max_h, style="FD")
        pdf.set_fill_color(255, 255, 255)

        pdf.set_xy(x0 + ROW_PADDING_MM, y0 + ROW_PADDING_MM)
        pdf.set_font(pdf.body_font, size=9)
        pdf.cell(label_width - ROW_PADDING_MM * 2, row_height, label, align="R")

        pdf.set_xy(x0 + label_width + ROW_PADDING_MM, y0 + ROW_PADDING_MM)
        pdf.cell(amount_col.width_mm - ROW_PADDING_MM * 2, row_height, amount, align=amount_col.align)
    finally:
        pdf.set_auto_page_break(auto_pb, margin=pdf.page_break_margin)

    pdf.set_xy(pdf.l_margin, y0 + max_h)
