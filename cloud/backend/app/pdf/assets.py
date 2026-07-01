"""Bundled PDF assets (fonts, default logos)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

DEJAVU_SANS = "DejaVuSans.ttf"
VENDIQO_LOGO = "vendiqo-logo.png"


def asset_path(name: str) -> Path:
    path = _ASSETS_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"PDF asset not found: {name}")
    return path


@lru_cache(maxsize=8)
def asset_bytes(name: str) -> bytes:
    return asset_path(name).read_bytes()
