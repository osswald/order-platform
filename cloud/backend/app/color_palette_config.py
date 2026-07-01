"""Organisation color palette validation and serialization."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_COLOR_PALETTE_ENTRIES = 32
MAX_COLOR_LABEL_CHARS = 64
_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ColorPaletteEntry(BaseModel):
    label: str = Field(..., min_length=1, max_length=MAX_COLOR_LABEL_CHARS)
    color: str

    @field_validator("label")
    @classmethod
    def _strip_label(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("label must not be empty")
        return text

    @field_validator("color")
    @classmethod
    def _normalize_color(cls, value: str) -> str:
        return normalize_hex_color(value)


class ColorPaletteRead(BaseModel):
    colors: list[ColorPaletteEntry] = Field(default_factory=list)


class ColorPaletteUpdate(BaseModel):
    colors: list[ColorPaletteEntry] = Field(default_factory=list, max_length=MAX_COLOR_PALETTE_ENTRIES)

    @model_validator(mode="after")
    def _validate_unique_colors(self) -> ColorPaletteUpdate:
        seen: set[str] = set()
        for entry in self.colors:
            key = entry.color.upper()
            if key in seen:
                raise ValueError("duplicate colors are not allowed")
            seen.add(key)
        return self


def normalize_hex_color(value: str) -> str:
    text = (value or "").strip()
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) == 4:
        text = f"#{text[1]}{text[1]}{text[2]}{text[2]}{text[3]}{text[3]}"
    text = text.upper()
    if not _HEX_COLOR_RE.match(text):
        raise ValueError("invalid hex color")
    return text


def read_color_palette_response(org: Any) -> ColorPaletteRead:
    raw = getattr(org, "color_palette", None)
    if not raw:
        return ColorPaletteRead(colors=[])
    if not isinstance(raw, list):
        return ColorPaletteRead(colors=[])
    colors: list[ColorPaletteEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            colors.append(ColorPaletteEntry.model_validate(item))
        except Exception:
            continue
    return ColorPaletteRead(colors=colors)


def apply_color_palette_update(org: Any, body: ColorPaletteUpdate) -> None:
    org.color_palette = [entry.model_dump() for entry in body.colors]
