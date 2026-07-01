"""Reusable table layout for PDF documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .base import VqPdf

Align = Literal["L", "C", "R"]


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


def write_table_header(pdf: VqPdf, spec: TableSpec) -> None:
    pdf.set_font(pdf.body_font, size=9)
    pdf.set_fill_color(240, 240, 240)
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    row_h = 6.0
    for col in spec.columns:
        pdf.set_xy(x0, y0)
        pdf.cell(col.width_mm, row_h, col.header, border=1, align=col.align, fill=True)
        x0 += col.width_mm
    pdf.ln(row_h)
    pdf.set_fill_color(255, 255, 255)


def write_table_row(
    pdf: VqPdf,
    spec: TableSpec,
    values: list[str],
    *,
    row_height: float = 5.5,
    continuation_rows: list[list[str]] | None = None,
) -> None:
    if pdf.get_y() > pdf.h - pdf.b_margin - row_height - 4:
        pdf.add_page()
        write_table_header(pdf, spec)

    padding = 0.8
    inner_pad = padding * 2
    rows = [values] + (continuation_rows or [])
    for row_idx, row_values in enumerate(rows):
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        max_h = row_height
        pdf.set_font(pdf.body_font, size=9)

        for col_idx, col in enumerate(spec.columns):
            text = row_values[col_idx] if col_idx < len(row_values) else ""
            inner_w = max(1.0, col.width_mm - inner_pad)
            line_count = len(
                pdf.multi_cell(
                    inner_w,
                    row_height,
                    text,
                    border=0,
                    align=col.align,
                    dry_run=True,
                    output="LINES",
                )
            )
            max_h = max(max_h, max(1, line_count) * row_height)

        x0 = pdf.l_margin
        for col in spec.columns:
            pdf.rect(x0, y0, col.width_mm, max_h)
            x0 += col.width_mm

        x0 = pdf.l_margin
        for col_idx, col in enumerate(spec.columns):
            text = row_values[col_idx] if col_idx < len(row_values) else ""
            pdf.set_xy(x0 + padding, y0 + padding)
            pdf.set_font(pdf.body_font, size=9)
            inner_w = max(1.0, col.width_mm - inner_pad)
            pdf.multi_cell(inner_w, row_height, text, border=0, align=col.align)
            x0 += col.width_mm

        pdf.set_xy(pdf.l_margin, y0 + max_h)
        if row_idx < len(rows) - 1:
            pdf.set_font(pdf.body_font, size=8)
            pdf.set_text_color(90, 90, 90)
        else:
            pdf.set_text_color(0, 0, 0)
