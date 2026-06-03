"""Shared PDF builder for Vendiqo manual test documents."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Callable

from fpdf import FPDF

TestCase = tuple[str, str, list[str], list[str], list[str]]


def font_path() -> str | None:
    candidates = []
    if platform.system() == "Darwin":
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
        )
    candidates.extend(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        if Path(path).is_file():
            return path
    return None


class TestPdf(FPDF):
    def __init__(self, header_title: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._header_title = header_title
        # Generous margins — cell(0) with custom fonts can clip on the right edge.
        self.set_margins(left=18, top=18, right=18)
        self.set_auto_page_break(auto=True, margin=20)
        font = font_path()
        if font:
            self.add_font("Body", "", font)
            self._body = "Body"
        else:
            self._body = "Helvetica"

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def _next_line(self, h: float) -> None:
        self.set_x(self.l_margin)
        self.ln(h)

    def _write_block(self, text: str, *, h: float = 5, size: int = 10, bold: bool = False) -> None:
        self.set_x(self.l_margin)
        self.set_font(self._body, size=size)
        self.multi_cell(
            self.content_width,
            h,
            text,
            new_x="LMARGIN",
            new_y="NEXT",
        )

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_x(self.l_margin)
        self.set_font(self._body, size=8)
        self.set_text_color(110, 110, 110)
        self.cell(self.content_width, 8, self._header_title, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self._next_line(2)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_x(self.l_margin)
        self.set_font(self._body, size=8)
        self.set_text_color(110, 110, 110)
        self.cell(self.content_width, 8, f"Page {self.page_no()}/{{nb}}", align="C")

    def cover_block(self, title: str, subtitle: str, intro: str) -> None:
        self._write_block(title, h=8, size=18)
        self._next_line(2)
        self._write_block(subtitle, h=6, size=11)
        self._next_line(3)
        self._write_block(intro, h=5, size=10)

    def section_title(self, title: str) -> None:
        if self.get_y() > 255:
            self.add_page()
        self._next_line(3)
        self.set_x(self.l_margin)
        self.set_font(self._body, size=12)
        self.set_fill_color(37, 99, 235)
        self.set_text_color(255, 255, 255)
        self.multi_cell(
            self.content_width,
            8,
            title,
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(0, 0, 0)
        self._next_line(2)

    def test_case(
        self,
        case_id: str,
        title: str,
        prerequisites: list[str],
        actions: list[str],
        expected: list[str],
    ) -> None:
        if self.get_y() > 250:
            self.add_page()

        self.set_x(self.l_margin)
        self.set_font(self._body, size=10)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(0, 0, 0)
        self.multi_cell(
            self.content_width,
            6,
            f"{case_id}  {title}",
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self._next_line(1)

        def block(label: str, items: list[str]) -> None:
            self.set_x(self.l_margin)
            self.set_font(self._body, size=9)
            self.set_text_color(30, 64, 175)
            self.multi_cell(
                self.content_width,
                5,
                label,
                new_x="LMARGIN",
                new_y="NEXT",
            )
            self.set_text_color(0, 0, 0)
            for item in items:
                self.set_x(self.l_margin)
                self.set_font(self._body, size=9)
                self.multi_cell(
                    self.content_width,
                    4.5,
                    f"  - {item}",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
            self._next_line(1)

        block("Prerequisites", prerequisites)
        block("Actions", actions)
        block("Expected outcome", expected)
        self._next_line(2)


def build_test_pdf(
    *,
    output: Path,
    title: str,
    subtitle: str,
    intro: str,
    groups: list[tuple[str, Callable[[str], bool]]],
    cases: list[TestCase],
) -> None:
    pdf = TestPdf(header_title=title)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.cover_block(title, subtitle, intro)

    for section_name, pred in groups:
        section_cases = [c for c in cases if pred(c[0])]
        if not section_cases:
            continue
        pdf.add_page()
        pdf.section_title(section_name)
        for case in section_cases:
            pdf.test_case(case[0], case[1], case[2], case[3], case[4])

    pdf.output(str(output))
    print(f"Wrote {output} ({len(cases)} test cases)")
