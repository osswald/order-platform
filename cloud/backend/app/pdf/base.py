"""Base PDF document class for Vendiqo cloud documents."""

from __future__ import annotations

import tempfile
from collections.abc import Iterable
from io import BytesIO

from fpdf import FPDF
from PIL import Image

from ..i18n import t
from .assets import DEJAVU_SANS, asset_path


class VqPdf(FPDF):
    MAX_LOGO_HEIGHT_MM = 18.0
    MAX_LOGO_WIDTH_MM = 35.0
    LOGO_GAP_MM = 4.0

    def __init__(self, *, locale: str = "de", title: str = "") -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.locale = locale
        self._doc_title = title
        self.body_font = "VqBody"
        self.set_margins(left=18, top=18, right=18)
        self.set_auto_page_break(auto=True, margin=20)
        self.alias_nb_pages()
        font_file = asset_path(DEJAVU_SANS)
        self.add_font(self.body_font, "", str(font_file))
        self.add_page()

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def write_heading(self, text: str, *, size: int = 14) -> None:
        self.set_x(self.l_margin)
        self.set_font(self.body_font, size=size)
        self.multi_cell(self.content_width, 7, text, new_x="LMARGIN", new_y="NEXT")

    def write_text(self, text: str, *, size: int = 10, gap: float = 5.0) -> None:
        self.set_x(self.l_margin)
        self.set_font(self.body_font, size=size)
        self.multi_cell(self.content_width, gap, text, new_x="LMARGIN", new_y="NEXT")

    def write_muted(self, text: str, *, size: int = 9) -> None:
        self.set_text_color(90, 90, 90)
        self.write_text(text, size=size, gap=4.5)
        self.set_text_color(0, 0, 0)

    def write_spacer(self, height_mm: float = 4.0) -> None:
        self.ln(height_mm)

    def _scaled_logo_mm(self, raw: bytes) -> tuple[bytes, float, float]:
        image = Image.open(BytesIO(raw))
        if image.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            alpha = image.convert("RGBA").split()[-1]
            background.paste(image.convert("RGBA"), mask=alpha)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        px_w, px_h = image.size
        if px_w <= 0 or px_h <= 0:
            return raw, 0.0, 0.0

        ratio = px_w / px_h
        width_mm = self.MAX_LOGO_WIDTH_MM
        height_mm = width_mm / ratio
        if height_mm > self.MAX_LOGO_HEIGHT_MM:
            height_mm = self.MAX_LOGO_HEIGHT_MM
            width_mm = height_mm * ratio

        target_w = max(1, int(px_w * (width_mm / (px_w * 0.264583))))
        target_h = max(1, int(px_h * (height_mm / (px_h * 0.264583))))
        resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        out = BytesIO()
        resized.save(out, format="PNG")
        return out.getvalue(), width_mm, height_mm

    def write_logo_header_block(
        self,
        logo_bytes: bytes | None,
        issuer_lines: Iterable[str],
    ) -> None:
        start_y = self.get_y()
        logo_w = 0.0
        logo_h = 0.0
        if logo_bytes:
            prepared, logo_w, logo_h = self._scaled_logo_mm(logo_bytes)
            if logo_w > 0 and logo_h > 0:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
                    tmp.write(prepared)
                    tmp.flush()
                    self.image(tmp.name, x=self.l_margin, y=start_y, w=logo_w, h=logo_h)

        text_x = self.l_margin + (logo_w + self.LOGO_GAP_MM if logo_w > 0 else 0.0)
        text_w = self.w - self.r_margin - text_x
        if text_w < 40:
            text_x = self.l_margin
            text_w = self.content_width

        self.set_xy(text_x, start_y)
        self.set_font(self.body_font, size=10)
        for line in issuer_lines:
            if line:
                self.multi_cell(text_w, 5, str(line), new_x="LMARGIN", new_y="NEXT")
                self.set_x(text_x)

        address_bottom = self.get_y()
        block_bottom = max(start_y + logo_h, address_bottom)
        self.set_y(block_bottom + 6)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font(self.body_font, size=8)
        self.set_text_color(110, 110, 110)
        page_label = f"{t('pdf.common.page', self.locale, page=self.page_no())} / {{nb}}"
        self.cell(0, 8, page_label, align="C")
        self.set_text_color(0, 0, 0)

    def output_bytes(self) -> bytes:
        out = self.output()
        if isinstance(out, bytearray):
            return bytes(out)
        if isinstance(out, bytes):
            return out
        return out.encode("latin-1")
